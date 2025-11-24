# backend/app/tasks/pipeline_chain.py

"""
High-level Celery workflow for the full dubbing chain.

NEW (Option A):
  - We now use a single external_ai /full call via task_full_chain.
  - JobSteps for the classic stages (asr, punctuate, translate, tts,
    separate_music, mix, replace_audio) are still created so the
    dashboard remains compatible. _finalize_job marks them all as
    succeeded once the full chain completes.
"""

import datetime
from celery import shared_task, chain
from app.database import db
from app.models.models import Job, JobStep
from app.tasks.progress_tracker import set_step_success

from .pipeline_tasks import (
    task_full_chain,  # 👈 NEW single-call task
)


def _calculate_text_metrics(payload: dict) -> dict:
    """Calculate text analytics metrics from pipeline payload."""
    metrics = {}
    
    try:
        english_text = payload.get("english", "")
        swahili_text = payload.get("swahili", "")
        english_segments = payload.get("english_segments", [])
        swahili_segments = payload.get("swahili_segments", [])
        
        # Word counts
        if english_text:
            metrics["english_word_count"] = len(english_text.split())
        if swahili_text:
            metrics["swahili_word_count"] = len(swahili_text.split())
        
        # Character counts
        if english_text:
            metrics["english_char_count"] = len(english_text)
        if swahili_text:
            metrics["swahili_char_count"] = len(swahili_text)
        
        # Segment counts
        if english_segments:
            metrics["segment_count"] = len(english_segments)
        elif swahili_segments:
            metrics["segment_count"] = len(swahili_segments)
        
        # Average segment duration and total duration
        if english_segments:
            durations = []
            for seg in english_segments:
                if isinstance(seg, dict):
                    start = seg.get("start", 0)
                    end = seg.get("end", 0)
                    if end > start:
                        durations.append(end - start)
            
            if durations:
                metrics["avg_segment_duration"] = sum(durations) / len(durations)
                metrics["total_duration"] = max(seg.get("end", 0) for seg in english_segments if isinstance(seg, dict))
        
        # Translation ratio (swahili words / english words)
        if metrics.get("english_word_count", 0) > 0 and metrics.get("swahili_word_count", 0) > 0:
            metrics["translation_ratio"] = metrics["swahili_word_count"] / metrics["english_word_count"]
        
    except Exception as e:
        # Don't fail the job if metrics calculation fails
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to calculate text metrics: {e}")
    
    return metrics


# The logical pipeline stages we still expose to the UI
PIPELINE_STEPS = [
    "asr",
    "punctuate",
    "translate",
    "tts",
    "separate_music",
    "mix",
    "replace_audio",
]


# ============================================================================
# MAIN ENTRY TASK
# ============================================================================
@shared_task(name="pipeline.run_chain", bind=True)
def run_chain(self, job_id: str, video_s3_uri: str):
    """
    Launch the entire dubbing pipeline for a video.

    Implementation:
      • Create JobStep rows for all stages (for UI compatibility)
      • Run a SINGLE Celery task (task_full_chain) that calls /full
      • Finalize job & mark all steps as succeeded in _finalize_job
    """

    job = Job.query.get(job_id)
    if not job:
        raise Exception(f"Job {job_id} not found")

    # Mark job running
    job.state = "running"
    job.started_at = datetime.datetime.utcnow()
    db.session.commit()

    # ----------------------------------------------------------------------
    # Ensure JobStep entries exist (one per pipeline logical stage)
    # ----------------------------------------------------------------------
    existing = {s.name for s in JobStep.query.filter_by(job_id=job_id).all()}
    for step in PIPELINE_STEPS:
        if step not in existing:
            db.session.add(JobStep(job_id=job_id, name=step, state="pending"))
    db.session.commit()

    # ----------------------------------------------------------------------
    # Chain definition: single full-chain task + finalizer
    # ----------------------------------------------------------------------
    workflow = chain(
        task_full_chain.s(video_s3_uri),
        _finalize_job.s(job_id),
    )

    async_result = workflow.apply_async()
    return {"task_id": async_result.id, "job_id": job_id}


def queue_dubbing_chain(job_id: str, video_s3_uri: str):
    """
    Called by Flask route /jobs/create.
    """
    from app.celery_app import celery_app

    return celery_app.send_task(
        "pipeline.run_chain",
        args=(job_id, video_s3_uri),
        queue="default",
    )


# ============================================================================
# FINALIZER
# ============================================================================
@shared_task(bind=True)
def _finalize_job(self, payload: dict, job_id: str):
    """
    Finalize job after successful pipeline completion.
    Marks all steps as succeeded and updates job state to 'succeeded'.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Mark all logical pipeline steps as successful for this job
        for step_name in PIPELINE_STEPS:
            set_step_success(job_id, step_name)

        job = Job.query.get(job_id)
        if not job:
            raise Exception(f"Job {job_id} not found for finalize step")

        # Check if job was already cancelled - don't overwrite cancelled state
        if job.state == "cancelled":
            logger.info(f"Job {job_id} was cancelled, skipping finalization")
            return payload

        job.state = "succeeded"
        job.current_step = "completed"
        job.progress = 100.0
        job.finished_at = datetime.datetime.utcnow()

        meta = dict(job.meta or {})
        # propagate output_s3_uri from payload
        if payload.get("output_s3_uri"):
            meta["output_s3_uri"] = payload.get("output_s3_uri")
        # Store transcriptions and translations (both plain text and timestamped segments)
        if payload.get("english"):
            meta["english"] = payload.get("english")
        if payload.get("swahili"):
            meta["swahili"] = payload.get("swahili")
        if payload.get("english_segments"):
            meta["english_segments"] = payload.get("english_segments")
        if payload.get("swahili_segments"):
            meta["swahili_segments"] = payload.get("swahili_segments")
        
        # Store pipeline metrics (ASR confidence, model versions, processing time, etc.)
        if payload.get("pipeline_metrics"):
            meta["pipeline_metrics"] = payload.get("pipeline_metrics")
        
        # Calculate and store text metrics
        text_metrics = _calculate_text_metrics(payload)
        if text_metrics:
            meta["text_metrics"] = text_metrics
        
        job.meta = meta

        db.session.commit()
        logger.info(f"Job {job_id} finalized successfully")

    except Exception as e:
        # If finalization fails, mark job as failed
        logger.error(f"Failed to finalize job {job_id}: {e}", exc_info=True)
        try:
            job = Job.query.get(job_id)
            if job and job.state != "cancelled":  # Don't overwrite cancelled state
                job.state = "failed"
                job.last_error_message = f"Finalization failed: {str(e)}"
                job.finished_at = datetime.datetime.utcnow()
                db.session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to mark job {job_id} as failed: {commit_error}")
        raise  # Re-raise to let Celery know the task failed

    payload["job_id"] = job_id
    return payload
