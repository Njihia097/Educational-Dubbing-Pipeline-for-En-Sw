# backend/app/routes/admin_routes.py
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from functools import wraps

import requests
from flask import Blueprint, jsonify, request
from sqlalchemy import func

from app.database import db
from app.models.models import Job, JobStep
from app.routes.auth_routes import require_admin
from app.utils.minio_client import get_minio_client

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# Simple in-memory cache for metrics (thread-safe for single worker)
_metrics_cache = {}
_cache_timestamps = {}


def cached_metrics(cache_seconds=5):
    """Decorator to cache endpoint results for specified seconds."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_key = f"{f.__name__}_{str(kwargs)}"
            now = time.time()
            
            if cache_key in _metrics_cache and (now - _cache_timestamps.get(cache_key, 0)) < cache_seconds:
                return _metrics_cache[cache_key]
            
            try:
                result = f(*args, **kwargs)
                # Only cache successful responses (status code 200)
                if isinstance(result, tuple) and len(result) == 2:
                    response, status_code = result
                    if status_code == 200:
                        _metrics_cache[cache_key] = result
                        _cache_timestamps[cache_key] = now
                else:
                    _metrics_cache[cache_key] = result
                    _cache_timestamps[cache_key] = now
                return result
            except Exception:
                # Don't cache errors, let them pass through
                raise
        return wrapper
    return decorator


# ------------------------------------------------------------------------------
# SYSTEM OVERVIEW ENDPOINTS
# ------------------------------------------------------------------------------

@admin_bp.route("/metrics/overview", methods=["GET"])
@cached_metrics(cache_seconds=10)
def metrics_overview():
    """Get system overview metrics: total jobs, jobs by state, avg processing time, active tasks."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        # Total jobs count
        total_jobs = db.session.query(func.count(Job.id)).scalar() or 0

        # Jobs by state
        jobs_by_state = (
            db.session.query(
                Job.state,
                func.count(Job.id).label("count")
            )
            .group_by(Job.state)
            .all()
        )
        state_counts = {state: count for state, count in jobs_by_state}

        # Average processing time (for succeeded jobs)
        avg_processing_time = (
            db.session.query(
                func.avg(
                    func.extract('epoch', Job.finished_at - Job.started_at)
                )
            )
            .filter(
                Job.state == "succeeded",
                Job.started_at.isnot(None),
                Job.finished_at.isnot(None)
            )
            .scalar()
        )
        avg_processing_time = float(avg_processing_time) if avg_processing_time else None

        # Active tasks (running + queued jobs)
        active_tasks = (
            db.session.query(func.count(Job.id))
            .filter(Job.state.in_(["queued", "running"]))
            .scalar() or 0
        )

        return jsonify({
            "total_jobs": total_jobs,
            "jobs_by_state": {
                "queued": state_counts.get("queued", 0),
                "running": state_counts.get("running", 0),
                "succeeded": state_counts.get("succeeded", 0),
                "failed": state_counts.get("failed", 0),
                "cancelled": state_counts.get("cancelled", 0),
            },
            "avg_processing_time_seconds": avg_processing_time,
            "active_tasks": active_tasks,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching overview metrics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/metrics/storage", methods=["GET"])
@cached_metrics(cache_seconds=60)
def metrics_storage():
    """Get MinIO storage usage for uploads and outputs buckets."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        client = get_minio_client()
        uploads_bucket = os.getenv("S3_BUCKET_UPLOADS", "uploads")
        outputs_bucket = os.getenv("S3_BUCKET_OUTPUTS", "outputs")

        def get_bucket_size(bucket_name):
            """Calculate total size of objects in a bucket."""
            try:
                if not client.bucket_exists(bucket_name):
                    return 0, 0
                
                total_size = 0
                object_count = 0
                for obj in client.list_objects(bucket_name, recursive=True):
                    total_size += obj.size
                    object_count += 1
                
                return total_size, object_count
            except Exception as e:
                logger.warning(f"Error calculating size for bucket {bucket_name}: {e}")
                return None, None

        uploads_size, uploads_count = get_bucket_size(uploads_bucket)
        outputs_size, outputs_count = get_bucket_size(outputs_bucket)

        total_size = (uploads_size or 0) + (outputs_size or 0)
        total_count = (uploads_count or 0) + (outputs_count or 0)

        return jsonify({
            "uploads": {
                "bucket": uploads_bucket,
                "size_bytes": uploads_size,
                "object_count": uploads_count,
            },
            "outputs": {
                "bucket": outputs_bucket,
                "size_bytes": outputs_size,
                "object_count": outputs_count,
            },
            "total": {
                "size_bytes": total_size,
                "object_count": total_count,
            },
        }), 200

    except Exception as e:
        logger.error(f"Error fetching storage metrics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/metrics/jobs-timeline", methods=["GET"])
@cached_metrics(cache_seconds=10)
def metrics_jobs_timeline():
    """Get job creation counts over time for chart visualization."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        days = int(request.args.get("days", 7))
        if days not in [7, 30, 90]:
            days = 7

        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Group by date (day) - PostgreSQL compatible
        timeline = (
            db.session.query(
                db.func.date(Job.created_at).label("date"),
                func.count(Job.id).label("count")
            )
            .filter(Job.created_at >= start_date)
            .group_by(db.func.date(Job.created_at))
            .order_by(db.func.date(Job.created_at))
            .all()
        )

        # Format for frontend
        timeline_data = [
            {
                "date": str(date),
                "count": count
            }
            for date, count in timeline
        ]

        return jsonify({
            "timeline": timeline_data,
            "days": days,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching jobs timeline: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------------------------
# WORKER + QUEUE MONITORING ENDPOINTS
# ------------------------------------------------------------------------------

@admin_bp.route("/monitoring/workers", methods=["GET"])
@cached_metrics(cache_seconds=3)
def monitoring_workers():
    """Get Celery worker status and active tasks."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        from app.celery_app import celery_app

        workers = []
        
        # Inspect active workers
        inspect = celery_app.control.inspect(timeout=2.0)
        
        # Get active tasks
        active_tasks = inspect.active() or {}
        
        # Get worker stats
        stats = inspect.stats() or {}
        
        # Get registered workers
        registered = inspect.registered() or {}
        
        # Combine information
        all_worker_names = set(active_tasks.keys()) | set(stats.keys()) | set(registered.keys())
        
        for worker_name in all_worker_names:
            worker_info = {
                "name": worker_name,
                "status": "online" if worker_name in active_tasks or worker_name in stats else "offline",
                "active_tasks": len(active_tasks.get(worker_name, [])),
                "stats": stats.get(worker_name, {}),
            }
            workers.append(worker_info)

        # If no workers found, return empty list
        if not workers:
            workers = [{"name": "No workers detected", "status": "offline", "active_tasks": 0, "stats": {}}]

        return jsonify({
            "workers": workers,
            "total_workers": len([w for w in workers if w["status"] == "online"]),
        }), 200

    except Exception as e:
        logger.error(f"Error inspecting Celery workers: {e}", exc_info=True)
        return jsonify({
            "workers": [],
            "total_workers": 0,
            "error": str(e)
        }), 200  # Return 200 with error message so frontend can display it


@admin_bp.route("/monitoring/queue", methods=["GET"])
@cached_metrics(cache_seconds=2)
def monitoring_queue():
    """Get Redis queue depth and pending task counts."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        import redis
        from app.celery_app import celery_app

        # Get Redis connection from Celery
        broker_url = celery_app.conf.broker_url
        redis_client = redis.from_url(broker_url)

        # Get queue length for default queue
        # Celery with Redis uses different key formats, try common ones
        queue_name = "default"
        queue_keys = [
            queue_name,  # Direct queue name
            f"celery",  # Default Celery queue
            f"{queue_name}:queue",  # Alternative format
        ]
        
        queue_length = 0
        for key in queue_keys:
            if redis_client.exists(key):
                queue_length = redis_client.llen(key)
                break

        # Get reserved tasks (tasks being processed)
        inspect = celery_app.control.inspect(timeout=2.0)
        active_tasks = inspect.active() or {}
        reserved_count = sum(len(tasks) for tasks in active_tasks.values())

        return jsonify({
            "queue_name": queue_name,
            "pending_tasks": queue_length,
            "reserved_tasks": reserved_count,
            "total_tasks": queue_length + reserved_count,
        }), 200

    except Exception as e:
        logger.error(f"Error checking queue status: {e}", exc_info=True)
        return jsonify({
            "queue_name": "default",
            "pending_tasks": None,
            "reserved_tasks": None,
            "total_tasks": None,
            "error": str(e)
        }), 200  # Return 200 with error so frontend can display it


@admin_bp.route("/monitoring/external-ai", methods=["GET"])
@cached_metrics(cache_seconds=5)
def monitoring_external_ai():
    """Check external AI service health and connectivity."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        external_ai_url = os.getenv("EXTERNAL_AI_URL", "http://host.docker.internal:7001")
        health_url = f"{external_ai_url.rstrip('/')}/health"

        start_time = time.time()
        response = requests.get(health_url, timeout=2.0)
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds

        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "status": "online",
                "response_time_ms": round(response_time, 2),
                "health_data": data,
                "url": health_url,
            }), 200
        else:
            return jsonify({
                "status": "error",
                "response_time_ms": round(response_time, 2),
                "error": f"HTTP {response.status_code}",
                "url": health_url,
            }), 200

    except requests.exceptions.Timeout:
        return jsonify({
            "status": "timeout",
            "response_time_ms": None,
            "error": "Connection timeout",
            "url": health_url if 'health_url' in locals() else "unknown",
        }), 200
    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "offline",
            "response_time_ms": None,
            "error": "Connection refused",
            "url": health_url if 'health_url' in locals() else "unknown",
        }), 200
    except Exception as e:
        logger.error(f"Error checking external AI health: {e}", exc_info=True)
        return jsonify({
            "status": "unknown",
            "response_time_ms": None,
            "error": str(e),
            "url": health_url if 'health_url' in locals() else "unknown",
        }), 200


# ------------------------------------------------------------------------------
# PIPELINE METRICS ENDPOINTS
# ------------------------------------------------------------------------------

@admin_bp.route("/metrics/pipeline", methods=["GET"])
@cached_metrics(cache_seconds=15)
def metrics_pipeline():
    """Get aggregated pipeline metrics: processing times, word counts, translation ratios."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        # Get all succeeded jobs and filter for those with text metrics
        all_succeeded = Job.query.filter(Job.state == "succeeded").all()
        succeeded_jobs = [j for j in all_succeeded if j.meta and j.meta.get("text_metrics")]

        # Aggregate text metrics
        total_english_words = 0
        total_swahili_words = 0
        total_english_chars = 0
        total_swahili_chars = 0
        total_videos = 0
        translation_ratios = []
        total_durations = []

        for job in succeeded_jobs:
            text_metrics = job.meta.get("text_metrics", {})
            if text_metrics:
                total_english_words += text_metrics.get("english_word_count", 0)
                total_swahili_words += text_metrics.get("swahili_word_count", 0)
                total_english_chars += text_metrics.get("english_char_count", 0)
                total_swahili_chars += text_metrics.get("swahili_char_count", 0)
                if text_metrics.get("translation_ratio"):
                    translation_ratios.append(text_metrics["translation_ratio"])
                if text_metrics.get("total_duration"):
                    total_durations.append(text_metrics["total_duration"])
                total_videos += 1

        # Calculate averages
        avg_words_per_video = total_english_words / total_videos if total_videos > 0 else 0
        avg_translation_ratio = sum(translation_ratios) / len(translation_ratios) if translation_ratios else None
        avg_video_duration = sum(total_durations) / len(total_durations) if total_durations else None

        # Calculate step durations from JobStep metrics
        step_durations = {}
        for step_name in ["asr", "punctuate", "translate", "tts", "separate_music", "mix", "replace_audio"]:
            steps = (
                JobStep.query
                .filter(JobStep.name == step_name)
                .filter(JobStep.state == "succeeded")
                .all()
            )
            if steps:
                durations = [
                    s.metrics.get("duration_seconds", 0) 
                    for s in steps 
                    if s.metrics and s.metrics.get("duration_seconds")
                ]
                if durations:
                    step_durations[step_name] = {
                        "avg": sum(durations) / len(durations),
                        "min": min(durations),
                        "max": max(durations),
                        "count": len(durations),
                    }

        return jsonify({
            "text_analytics": {
                "total_english_words": total_english_words,
                "total_swahili_words": total_swahili_words,
                "total_english_chars": total_english_chars,
                "total_swahili_chars": total_swahili_chars,
                "total_videos_processed": total_videos,
                "avg_words_per_video": round(avg_words_per_video, 2),
                "avg_translation_ratio": round(avg_translation_ratio, 3) if avg_translation_ratio else None,
                "avg_video_duration_seconds": round(avg_video_duration, 2) if avg_video_duration else None,
            },
            "step_durations": step_durations,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching pipeline metrics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/metrics/pipeline/steps", methods=["GET"])
@cached_metrics(cache_seconds=15)
def metrics_pipeline_steps():
    """Get step-by-step performance metrics: durations, success rates, retry rates."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        step_names = ["asr", "punctuate", "translate", "tts", "separate_music", "mix", "replace_audio"]
        step_stats = {}

        for step_name in step_names:
            all_steps = JobStep.query.filter(JobStep.name == step_name).all()
            succeeded_steps = [s for s in all_steps if s.state == "succeeded"]
            failed_steps = [s for s in all_steps if s.state == "failed"]
            
            total_count = len(all_steps)
            success_count = len(succeeded_steps)
            failed_count = len(failed_steps)
            retry_count = sum(s.retry_count or 0 for s in all_steps)

            # Calculate durations for succeeded steps
            durations = []
            for step in succeeded_steps:
                if step.metrics and step.metrics.get("duration_seconds"):
                    durations.append(step.metrics["duration_seconds"])
                elif step.started_at and step.finished_at:
                    # Normalize datetimes to avoid timezone mismatch
                    started = step.started_at
                    finished = step.finished_at
                    # Handle timezone-aware datetimes
                    if started.tzinfo is not None:
                        started = started.astimezone(timezone.utc).replace(tzinfo=None)
                    if finished.tzinfo is not None:
                        finished = finished.astimezone(timezone.utc).replace(tzinfo=None)
                    durations.append((finished - started).total_seconds())

            step_stats[step_name] = {
                "total_count": total_count,
                "success_count": success_count,
                "failed_count": failed_count,
                "retry_count": retry_count,
                "success_rate": round(success_count / total_count * 100, 2) if total_count > 0 else 0,
                "retry_rate": round(retry_count / total_count * 100, 2) if total_count > 0 else 0,
                "avg_duration_seconds": round(sum(durations) / len(durations), 2) if durations else None,
                "min_duration_seconds": round(min(durations), 2) if durations else None,
                "max_duration_seconds": round(max(durations), 2) if durations else None,
            }

        return jsonify({
            "steps": step_stats,
        }), 200

    except Exception as e:
        logger.error(f"Error fetching pipeline step metrics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500


@admin_bp.route("/metrics/pipeline/text-analytics", methods=["GET"])
@cached_metrics(cache_seconds=15)
def metrics_pipeline_text_analytics():
    """Get text analytics aggregations: word counts, translation ratios, segment stats."""
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        # Get all succeeded jobs and filter for those with text metrics
        all_succeeded = Job.query.filter(Job.state == "succeeded").all()
        succeeded_jobs = [j for j in all_succeeded if j.meta and j.meta.get("text_metrics")]

        word_counts_en = []
        word_counts_sw = []
        char_counts_en = []
        char_counts_sw = []
        segment_counts = []
        translation_ratios = []
        segment_durations = []
        video_durations = []

        for job in succeeded_jobs:
            text_metrics = job.meta.get("text_metrics", {})
            if text_metrics:
                if text_metrics.get("english_word_count"):
                    word_counts_en.append(text_metrics["english_word_count"])
                if text_metrics.get("swahili_word_count"):
                    word_counts_sw.append(text_metrics["swahili_word_count"])
                if text_metrics.get("english_char_count"):
                    char_counts_en.append(text_metrics["english_char_count"])
                if text_metrics.get("swahili_char_count"):
                    char_counts_sw.append(text_metrics["swahili_char_count"])
                if text_metrics.get("segment_count"):
                    segment_counts.append(text_metrics["segment_count"])
                if text_metrics.get("translation_ratio"):
                    translation_ratios.append(text_metrics["translation_ratio"])
                if text_metrics.get("avg_segment_duration"):
                    segment_durations.append(text_metrics["avg_segment_duration"])
                if text_metrics.get("total_duration"):
                    video_durations.append(text_metrics["total_duration"])

        def calc_stats(values):
            if not values:
                return None
            return {
                "min": round(min(values), 2),
                "max": round(max(values), 2),
                "avg": round(sum(values) / len(values), 2),
                "median": round(sorted(values)[len(values) // 2], 2) if values else None,
                "total": sum(values),
                "count": len(values),
            }

        return jsonify({
            "english_word_count": calc_stats(word_counts_en),
            "swahili_word_count": calc_stats(word_counts_sw),
            "english_char_count": calc_stats(char_counts_en),
            "swahili_char_count": calc_stats(char_counts_sw),
            "segment_count": calc_stats(segment_counts),
            "translation_ratio": calc_stats(translation_ratios),
            "avg_segment_duration": calc_stats(segment_durations),
            "video_duration": calc_stats(video_durations),
        }), 200

    except Exception as e:
        logger.error(f"Error fetching text analytics: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

