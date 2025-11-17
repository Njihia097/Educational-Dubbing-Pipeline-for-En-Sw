import datetime
import os
import tempfile
import uuid
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from flask import Blueprint, request, jsonify

from app.database import db
from app.models.models import AppUser, Project, Job, JobStep, JobOutput, Asset

# Lazily load heavy dependencies when needed (avoid circular imports during app init)
celery_app = None
upload_file = None
queue_dubbing_chain = None
TESTING_ENV = os.getenv("FLASK_ENV") == "testing" or os.getenv("TESTING") == "1"


def _ensure_dependencies():
    global celery_app, upload_file, queue_dubbing_chain
    if celery_app is None:
        from app.celery_app import celery_app as _celery
        celery_app = _celery
    if upload_file is None:
        from app.utils.minio_client import upload_file as _upload
        upload_file = _upload
    if queue_dubbing_chain is None:
        from app.tasks.pipeline_chain import queue_dubbing_chain as _queue
        queue_dubbing_chain = _queue
job_bp = Blueprint("job_bp", __name__)


@job_bp.route("/create", methods=["POST"])
def create_job():
    if not TESTING_ENV:
        _ensure_dependencies()

    if upload_file is None or queue_dubbing_chain is None:
        return jsonify({"error": "Job creation disabled in testing mode"}), 503

    file = request.files.get("file")
    owner_id = request.form.get("owner_id")
    project_id = request.form.get("project_id")

    if not file:
        return jsonify({"error": "Missing file"}), 400

    try:
        owner = _resolve_owner(owner_id)
        project = _resolve_project(project_id, owner.id)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    # Save temporarily before MinIO upload
    # Use the persistent uploads volume instead of ephemeral /tmp
    default_tmp_root = "/data/uploads/tmp"
    tmp_dir = Path(os.getenv("JOB_UPLOAD_TMP", default_tmp_root))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = tmp_dir / f"{uuid.uuid4()}_{file.filename}"
    file.save(str(temp_path))

    if not temp_path.exists():
        # Defensive sanity check to make failures obvious
        raise FileNotFoundError(f"Upload temp file was not created: {temp_path}")

    # Upload to MinIO (use S3_* env, but default is still 'uploads')
    bucket = os.getenv("S3_BUCKET_UPLOADS", os.getenv("MINIO_BUCKET_UPLOADS", "uploads"))
    object_name = f"{owner.id}/{uuid.uuid4()}_{file.filename}"
    s3_uri = upload_file(bucket, object_name, str(temp_path))

    # Remove temp file
    if temp_path.exists():
        temp_path.unlink()

    # Create Asset entry for uploaded file
    asset = Asset(
        owner_id=owner.id,
        project_id=project.id if project else None,
        kind="video",
        uri=s3_uri,
        meta={"original_name": file.filename},
    )
    db.session.add(asset)
    db.session.flush()

    # Create Job entry
    job = Job(
        owner_id=owner.id,
        project_id=project.id if project else None,
        input_asset_id=asset.id,
        state="queued",
        meta={"pipeline": "local_dubbing"},
        created_at=datetime.datetime.now(datetime.UTC),
    )
    db.session.add(job)
    db.session.flush()

    # Create default steps + output placeholders
    for step in ["asr", "translation", "tts", "lipsync", "finalize"]:
        db.session.add(JobStep(job_id=job.id, name=step, state="pending"))
    for output_kind in ["translated_text", "tts_audio", "lipsynced_video", "subtitle"]:
        db.session.add(JobOutput(job_id=job.id, kind=output_kind, meta={}))

    db.session.commit()

    try:
        task = queue_dubbing_chain(str(job.id), s3_uri)
        return jsonify(
            {
                "job_id": str(job.id),
                "task_id": task.id,
                "message": "Job created successfully",
                "uri": s3_uri,
                "state": job.state,
            }
        ), 201
    except Exception as e:
        job.state = "failed"
        job.error_code = str(e)
        db.session.commit()
        return jsonify({"error": f"Failed to start task: {e}"}), 500


def _resolve_owner(owner_id: str | None) -> AppUser:
    """
    Accept UUIDs from the client but allow smoke-test shorthand (None or "1")
    by provisioning a default user if needed.
    """
    if not owner_id or owner_id in {"1", "default", "auto"}:
        user = AppUser.query.first()
        if user:
            return user
        user = AppUser(
            email="smoke-test@example.com",
            display_name="Smoke Tester",
            password_hash="smoke-test",
        )
        db.session.add(user)
        db.session.commit()
        return user

    try:
        owner_uuid = UUID(owner_id)
    except ValueError as exc:
        raise ValueError("owner_id must be a valid UUID") from exc

    user = db.session.get(AppUser, owner_uuid)
    if not user:
        raise ValueError(f"Owner {owner_uuid} not found")
    return user


def _resolve_project(project_id: str | None, owner_uuid) -> Project | None:
    """
    Same as _resolve_owner but scoped to the owner's projects.
    Returns None if the system can operate without a project reference.
    """
    if not project_id or project_id in {"1", "default", "auto"}:
        project = Project.query.filter_by(owner_id=owner_uuid).first()
        if project:
            return project
        project = Project(owner_id=owner_uuid, name="Smoke Test Project")
        db.session.add(project)
        db.session.commit()
        return project

    try:
        project_uuid = UUID(project_id)
    except ValueError as exc:
        raise ValueError("project_id must be a valid UUID") from exc

    project = db.session.get(Project, project_uuid)
    if not project:
        raise ValueError(f"Project {project_uuid} not found")
    return project


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

    api_state = "completed" if job.state == "succeeded" else job.state

    return jsonify({
        "id": str(job.id),
        "state": api_state,
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
