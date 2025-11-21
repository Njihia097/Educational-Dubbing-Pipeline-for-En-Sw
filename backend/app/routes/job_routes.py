import datetime
import os
import uuid
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from flask import Blueprint, request, jsonify

from app.database import db
from app.models.models import AppUser, Project, Job, JobStep, JobOutput, Asset
from app.routes.auth_routes import get_current_user, require_admin  # 🔐 RBAC helpers

# Lazily load heavy dependencies when needed (avoid circular imports)
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


# ------------------------------------------------------------------------------
# JOB CREATION
# ------------------------------------------------------------------------------
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
    default_tmp_root = "/data/uploads/tmp"
    tmp_dir = Path(os.getenv("JOB_UPLOAD_TMP", default_tmp_root))
    tmp_dir.mkdir(parents=True, exist_ok=True)

    temp_path = tmp_dir / f"{uuid.uuid4()}_{file.filename}"
    file.save(str(temp_path))

    if not temp_path.exists():
        raise FileNotFoundError(f"Upload temp file was not created: {temp_path}")

    bucket = os.getenv("S3_BUCKET_UPLOADS", os.getenv("MINIO_BUCKET_UPLOADS", "uploads"))
    object_name = f"{owner.id}/{uuid.uuid4()}_{file.filename}"
    s3_uri = upload_file(bucket, object_name, str(temp_path))

    # delete temp file
    if temp_path.exists():
        temp_path.unlink()

    # Store Asset
    asset = Asset(
        owner_id=owner.id,
        project_id=project.id if project else None,
        kind="video",
        uri=s3_uri,
        meta={"original_name": file.filename},
    )
    db.session.add(asset)
    db.session.flush()

    # Create Job
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

    # Exact pipeline steps (must match pipeline decorators)
    for step in [
        "asr",
        "punctuate",
        "translate",
        "tts",
        "separate_music",
        "mix",
        "replace_audio",
    ]:
        db.session.add(JobStep(job_id=job.id, name=step, state="pending"))

    # Output placeholders
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


# ------------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------------
def _resolve_owner(owner_id: str | None) -> AppUser:
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


def _serialize_job_brief(job: Job, asset: Asset | None = None, owner: AppUser | None = None):
    """Compact job representation for dashboard tables."""
    if asset is None and job.input_asset_id:
        asset = db.session.get(Asset, job.input_asset_id)
    if owner is None and job.owner_id:
        owner = db.session.get(AppUser, job.owner_id)

    meta = dict(job.meta or {})
    return {
        "id": str(job.id),
        "state": job.state,
        "current_step": job.current_step,
        "progress": _safe_serialize(getattr(job, "progress", None)),
        "retry_count": job.retry_count or 0,
        "last_error_message": job.last_error_message,
        "created_at": _safe_serialize(job.created_at),
        "started_at": _safe_serialize(job.started_at),
        "finished_at": _safe_serialize(job.finished_at),
        "input_s3_uri": asset.uri if asset else None,
        "output_s3_uri": meta.get("output_s3_uri"),
        "video_name": (asset.meta or {}).get("original_name") if asset else None,
        "owner_email": owner.email if owner else None,
    }


# ------------------------------------------------------------------------------
# STATUS ENDPOINT (includes retry info + URIs)
# ------------------------------------------------------------------------------
@job_bp.route("/status/<job_id>", methods=["GET"])
def job_status(job_id):
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Resolve input asset
    asset = db.session.get(Asset, job.input_asset_id) if job.input_asset_id else None

    # Build steps list
    steps = []
    for s in JobStep.query.filter_by(job_id=job_id).all():
        step_progress = getattr(s, "progress", None)
        steps.append(
            {
                "name": s.name,
                "state": s.state,
                "progress": _safe_serialize(step_progress),
                "started_at": _safe_serialize(getattr(s, "started_at", None)),
                "finished_at": _safe_serialize(getattr(s, "finished_at", None)),
            }
        )

    meta = _safe_serialize(dict(job.meta or {}))
    if getattr(job, "progress", None) is not None:
        meta["progress"] = _safe_serialize(job.progress)
    if getattr(job, "current_step", None) is not None:
        meta["current_step"] = _safe_serialize(job.current_step)

    api_state = "completed" if job.state == "succeeded" else job.state

    # input & output URIs
    input_s3_uri = asset.uri if asset else None
    output_s3_uri = meta.get("output_s3_uri")

    return jsonify(
        {
            "id": str(job.id),
            "state": api_state,
            "current_step": _safe_serialize(getattr(job, "current_step", None)),
            "progress": _safe_serialize(getattr(job, "progress", None)),
            "steps": steps,
            "retry_count": job.retry_count or 0,
            "last_error_message": job.last_error_message,
            "error": getattr(job, "error_message", None),
            "meta": meta,
            "input_s3_uri": input_s3_uri,
            "output_s3_uri": output_s3_uri,
            "created_at": _safe_serialize(job.created_at),
            "started_at": _safe_serialize(job.started_at),
            "finished_at": _safe_serialize(job.finished_at),
        }
    ), 200


# ------------------------------------------------------------------------------
# LIST CURRENT USER'S JOBS (with pagination + filters)
# ------------------------------------------------------------------------------
@job_bp.route("/my", methods=["GET"])
def list_my_jobs():
    """Return jobs for the currently logged-in user."""
    user = get_current_user()
    if not user:
        return jsonify({"error": "Authentication required"}), 401

    # pagination
    try:
        page = max(int(request.args.get("page", "1")), 1)
    except ValueError:
        page = 1
    try:
        page_size = max(min(int(request.args.get("page_size", "20")), 100), 1)
    except ValueError:
        page_size = 20

    state_filter = request.args.get("state") or ""
    search = (request.args.get("search") or "").strip()

    query = Job.query.filter_by(owner_id=user.id)

    if state_filter:
        query = query.filter(Job.state == state_filter)

    # simple search: by video filename (Asset.meta.original_name) or job id
    if search:
        search_like = f"%{search.lower()}%"

        query = (
            query.join(Asset, Job.input_asset_id == Asset.id, isouter=True)
            .filter(
                db.or_(
                    db.func.lower(db.func.cast(Job.id, db.Text)).like(search_like),
                    db.func.lower(
                        db.func.coalesce(
                            db.func.cast(Asset.meta['original_name'], db.Text),
                            ''
                        )
                    ).like(search_like),
                )
            )
        )


    total = query.count()
    jobs = (
        query.order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return jsonify(
        {
            "jobs": [_serialize_job_brief(job) for job in jobs],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total // page_size) + (1 if total % page_size else 0),
        }
    ), 200


# ------------------------------------------------------------------------------
# ADMIN: LIST ALL JOBS (with pagination + filters)
# ------------------------------------------------------------------------------
@job_bp.route("/admin", methods=["GET"])
def admin_list_jobs():
    """
    Admin-only endpoint:
      - lists all jobs (most recent first)
      - supports pagination, state filter, search
    """
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    try:
        page = max(int(request.args.get("page", "1")), 1)
    except ValueError:
        page = 1
    try:
        page_size = max(min(int(request.args.get("page_size", "50")), 200), 1)
    except ValueError:
        page_size = 50

    state_filter = request.args.get("state") or ""
    search = (request.args.get("search") or "").strip()

    query = Job.query

    if state_filter:
        query = query.filter(Job.state == state_filter)

    if search:
        search_like = f"%{search.lower()}%"

        query = (
            query.join(Asset, Job.input_asset_id == Asset.id, isouter=True)
            .join(AppUser, Job.owner_id == AppUser.id, isouter=True)
            .filter(
                db.or_(
                    db.func.lower(db.func.cast(Job.id, db.Text)).like(search_like),
                    db.func.lower(AppUser.email).like(search_like),
                    db.func.lower(
                        db.func.coalesce(
                            db.func.cast(Asset.meta['original_name'], db.Text),
                            ''
                        )
                    ).like(search_like),
                )
            )
        )


    total = query.count()
    jobs = (
        query.order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result = []
    for job in jobs:
        asset = db.session.get(Asset, job.input_asset_id) if job.input_asset_id else None
        owner = db.session.get(AppUser, job.owner_id) if job.owner_id else None
        result.append(_serialize_job_brief(job, asset=asset, owner=owner))

    return jsonify(
        {
            "jobs": result,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total // page_size) + (1 if total % page_size else 0),
        }
    ), 200


# ------------------------------------------------------------------------------
# PRESIGNED URL ENDPOINT
# ------------------------------------------------------------------------------
@job_bp.route("/presign", methods=["GET"])
def presign_download():
    bucket = request.args.get("bucket", "uploads")
    object_name = request.args.get("object")
    if not object_name:
        return jsonify({"error": "Missing object parameter"}), 400

    from app.utils.minio_client import presign_url

    try:
        url = presign_url(
            bucket,
            object_name,
            extra_headers={
                "response-content-type": "video/mp4",
                "response-content-disposition": "inline",
            },
        )

        return jsonify({"url": url, "expires_in": 3600}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------------------------
# RETRY ENDPOINT — restart a single job
# ------------------------------------------------------------------------------
@job_bp.route("/<job_id>/retry", methods=["POST"])
def retry_job(job_id):
    """
    Manually restart a job that has failed / completed.
    This:
      • validates job exists
      • resets job + step state
      • re-queues the full dubbing pipeline
    """
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    # Only allow retry from terminal states
    if job.state not in ("failed", "cancelled", "succeeded", "completed"):
        return jsonify({"error": f"Job is in state '{job.state}', cannot retry"}), 400

    # Resolve original input URI
    asset = db.session.get(Asset, job.input_asset_id) if job.input_asset_id else None
    if not asset:
        return jsonify({"error": "Input asset not found, cannot retry"}), 400

    # Reset job fields
    job.state = "queued"
    job.error_code = None
    job.current_step = None
    job.progress = 0.0
    job.started_at = None
    job.finished_at = None

    # Increment job retry counter (manual retries)
    job.retry_count = (job.retry_count or 0) + 1
    job.last_error_message = None

    # Clear output reference from meta
    meta = dict(job.meta or {})
    meta.pop("output_s3_uri", None)
    job.meta = meta

    # Reset all JobStep rows
    steps = JobStep.query.filter_by(job_id=job.id).all()
    for s in steps:
        s.state = "pending"
        s.started_at = None
        s.finished_at = None
        s.metrics = {}
        s.retry_count = 0

    db.session.commit()

    # Requeue pipeline (unless in testing mode)
    if not TESTING_ENV:
        _ensure_dependencies()
        if queue_dubbing_chain is None:
            return jsonify({"error": "Retry disabled: queue not available"}), 503

        task = queue_dubbing_chain(str(job.id), asset.uri)
        return jsonify(
            {
                "job_id": str(job.id),
                "task_id": task.id,
                "message": "Job retry queued successfully",
                "state": job.state,
            }
        ), 200

    # In testing, just return updated job
    return jsonify(
        {
            "job_id": str(job.id),
            "message": "Job reset for retry (testing mode, no task queued)",
            "state": job.state,
        }
    ), 200


# ------------------------------------------------------------------------------
# ADMIN BULK RETRY — retry all failed jobs
# ------------------------------------------------------------------------------
@job_bp.route("/admin/retry_failed", methods=["POST"])
def admin_retry_failed_jobs():
    if not require_admin():
        return jsonify({"error": "Admin privileges required"}), 403

    failed_jobs = Job.query.filter(Job.state == "failed").all()
    if not failed_jobs:
        return jsonify({"message": "No failed jobs to retry", "count": 0}), 200

    if not TESTING_ENV:
        _ensure_dependencies()
        if queue_dubbing_chain is None:
            return jsonify({"error": "Retry disabled: queue not available"}), 503

    count = 0
    job_ids = []

    for job in failed_jobs:
        asset = db.session.get(Asset, job.input_asset_id) if job.input_asset_id else None
        if not asset:
            continue

        # reset state
        job.state = "queued"
        job.error_code = None
        job.current_step = None
        job.progress = 0.0
        job.started_at = None
        job.finished_at = None
        job.retry_count = (job.retry_count or 0) + 1
        job.last_error_message = None

        meta = dict(job.meta or {})
        meta.pop("output_s3_uri", None)
        job.meta = meta

        steps = JobStep.query.filter_by(job_id=job.id).all()
        for s in steps:
            s.state = "pending"
            s.started_at = None
            s.finished_at = None
            s.metrics = {}
            s.retry_count = 0

        job_ids.append(str(job.id))
        count += 1

        if not TESTING_ENV:
            queue_dubbing_chain(str(job.id), asset.uri)

    db.session.commit()

    return jsonify(
        {
            "message": f"Queued retry for {count} failed jobs",
            "count": count,
            "job_ids": job_ids,
        }
    ), 200


# ------------------------------------------------------------------------------
# JOB LOGS – structured + combined text log
# ------------------------------------------------------------------------------
@job_bp.route("/<job_id>/logs", methods=["GET"])
def job_logs(job_id):
    """
    Returns structured logs + combined text representation.

    Shape:
    {
      "job": {...brief...},
      "steps": [
        {
          "name": "...",
          "state": "...",
          "retry_count": 0,
          "started_at": "...",
          "finished_at": "...",
          "metrics": {...},
          "log_ref": "..."
        },
        ...
      ],
      "text_log": "ASR: ...\nTRANSLATE: ..."
    }
    """
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    user = get_current_user()
    is_admin = require_admin()

    # Only owner or admin can view logs
    if not is_admin and (not user or user.id != job.owner_id):
        return jsonify({"error": "Not authorized to view logs for this job"}), 403

    asset = db.session.get(Asset, job.input_asset_id) if job.input_asset_id else None
    owner = db.session.get(AppUser, job.owner_id) if job.owner_id else None

    steps = (
        JobStep.query.filter_by(job_id=job.id)
        .order_by(JobStep.started_at.asc().nullsfirst())
        .all()
    )

    steps_payload = []
    text_lines = []

    header = f"Job {job.id} | state={job.state} | retries={job.retry_count or 0}"
    if job.last_error_message:
        header += f" | last_error={job.last_error_message}"
    text_lines.append(header)

    for s in steps:
        step_entry = {
            "name": s.name,
            "state": s.state,
            "retry_count": s.retry_count or 0,
            "started_at": _safe_serialize(s.started_at),
            "finished_at": _safe_serialize(s.finished_at),
            "metrics": s.metrics or {},
            "log_ref": s.log_ref,
        }
        steps_payload.append(step_entry)

        line = f"STEP {s.name}: state={s.state}, retries={s.retry_count or 0}"
        if s.started_at:
            line += f", started_at={_safe_serialize(s.started_at)}"
        if s.finished_at:
            line += f", finished_at={_safe_serialize(s.finished_at)}"
        if s.log_ref:
            line += f", log_ref={s.log_ref}"
        text_lines.append(line)

    job_brief = _serialize_job_brief(job, asset=asset, owner=owner)

    return jsonify(
        {
            "job": job_brief,
            "steps": steps_payload,
            "text_log": "\n".join(text_lines),
        }
    ), 200
