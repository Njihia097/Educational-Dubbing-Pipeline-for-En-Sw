import datetime
import os
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from flask import Blueprint, request, jsonify

from app.database import db
from app.models.models import Job, JobStep, JobOutput, Asset

# Lazy import guard to prevent Celery/MinIO blocking during tests
TESTING = os.getenv("FLASK_ENV") == "testing" or os.getenv("TESTING") == "1"
if not TESTING:
    from app.celery_app import celery_app
    from app.utils.minio_client import upload_file
else:
    celery_app = None
    upload_file = None

job_bp = Blueprint("job_bp", __name__)


@job_bp.route("/create", methods=["POST"])
def create_job():
    if upload_file is None or celery_app is None:
        return (
            jsonify({"error": "Job creation disabled in testing mode"}),
            503,
        )

    file = request.files.get("file")
    owner_id = request.form.get("owner_id")
    project_id = request.form.get("project_id")

    if not file or not owner_id:
        return jsonify({"error": "Missing file or owner_id"}), 400

    # Save temporarily before MinIO upload
    tmp_dir = Path(os.getenv("JOB_UPLOAD_TMP", tempfile.gettempdir()))
    tmp_dir.mkdir(parents=True, exist_ok=True)
    temp_path = tmp_dir / f"{uuid.uuid4()}_{file.filename}"
    file.save(temp_path)

    # Upload to MinIO
    bucket = os.getenv("MINIO_BUCKET_UPLOADS", "uploads")
    object_name = f"{owner_id}/{uuid.uuid4()}_{file.filename}"
    s3_uri = upload_file(bucket, object_name, str(temp_path))

    # Remove temp file
    if temp_path.exists():
        temp_path.unlink()

    # Create Asset entry for uploaded file
    asset = Asset(
        owner_id=owner_id,
        project_id=project_id,
        kind="video",
        uri=s3_uri,
        meta={"original_name": file.filename}
    )
    db.session.add(asset)
    db.session.flush()

    # Create Job entry
    job = Job(
        owner_id=owner_id,
        project_id=project_id,
        input_asset_id=asset.id,
        state="queued",
        meta={"pipeline": "local_dubbing"},
        created_at=datetime.datetime.now(datetime.UTC),
    )
    db.session.add(job)
    db.session.flush()

    # Create default steps + output placeholders
    for step in ["asr", "translation", "tts", "lipsync"]:
        db.session.add(JobStep(job_id=job.id, name=step, state="pending"))
    for output_kind in ["translated_text", "tts_audio", "lipsynced_video", "subtitle"]:
        db.session.add(JobOutput(job_id=job.id, kind=output_kind, meta={}))

    db.session.commit()

    try:
        task = celery_app.send_task("pipeline.run_dubbing", args=[str(job.id), s3_uri])
        return jsonify({
            "job_id": str(job.id),
            "task_id": task.id,
            "message": "Job created successfully",
            "uri": s3_uri,
            "state": job.state
        }), 201
    except Exception as e:
        job.state = "failed"
        job.error_code = str(e)
        db.session.commit()
        return jsonify({"error": f"Failed to start task: {e}"}), 500


def _safe_serialize(value):
    """Convert DB values (Decimal, UUID, datetime, nested dicts/lists) into JSON-safe primitives."""
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, (datetime.date, datetime.time)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {k: _safe_serialize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_safe_serialize(v) for v in value]
    return value


@job_bp.route("/status/<job_id>", methods=["GET"])
def job_status(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    steps = []
    for s in JobStep.query.filter_by(job_id=job_id).all():
        # tolerate missing 'progress' column if not migrated yet
        step_progress = getattr(s, "progress", None)
        steps.append({
            "name": s.name,
            "state": s.state,
            "progress": _safe_serialize(step_progress),
            "started_at": _safe_serialize(getattr(s, "started_at", None)),
            "finished_at": _safe_serialize(getattr(s, "finished_at", None)),
        })

    # Back-compat meta while keeping top-level fields
    meta = _safe_serialize(dict(job.meta or {}))
    if getattr(job, "progress", None) is not None:
        meta["progress"] = _safe_serialize(job.progress)
    if getattr(job, "current_step", None) is not None:
        meta["current_step"] = _safe_serialize(job.current_step)

    return jsonify({
        "id": str(job.id),
        "state": job.state,
        "current_step": _safe_serialize(getattr(job, "current_step", None)),
        "progress": _safe_serialize(getattr(job, "progress", None)),
        "steps": steps,
        "error": getattr(job, "error_message", None),
        "meta": meta,  # <-- matches the test’s expectation
        "created_at": _safe_serialize(job.created_at),
        "started_at": _safe_serialize(job.started_at),
        "finished_at": _safe_serialize(job.finished_at),
    }), 200



@job_bp.route("/presign", methods=["GET"])
def presign_download():
    """Generate presigned URL for accessing uploaded assets."""
    bucket = request.args.get("bucket", "uploads")
    object_name = request.args.get("object")
    if not object_name:
        return jsonify({"error": "Missing object parameter"}), 400

    from app.utils.minio_client import presign_url
    try:
        url = presign_url(bucket, object_name)
        return jsonify({"url": url, "expires_in": 3600}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

