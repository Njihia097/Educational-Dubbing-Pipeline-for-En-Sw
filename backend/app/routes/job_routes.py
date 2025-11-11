from flask import Blueprint, request, jsonify
from app.database import db
from app.models.models import Job, Asset
from app.celery_app import celery_app
import os, uuid

job_bp = Blueprint("job_bp", __name__)

@job_bp.route("/create", methods=["POST"])
def create_job():
    """
    Creates a new dubbing job, stores the input file as an Asset,
    and queues Celery task for processing.
    """
    file = request.files.get("file")
    owner_id = request.form.get("owner_id")
    project_id = request.form.get("project_id")

    if not file or not owner_id:
        return jsonify({"error": "Missing file or owner_id"}), 400

    upload_dir = "/data/uploads"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    file.save(file_path)

    # Create asset for the uploaded file
    asset = Asset(
        owner_id=owner_id,
        project_id=project_id,
        kind="video",
        uri=file_path,
        meta={"original_name": file.filename}
    )
    db.session.add(asset)
    db.session.flush()  # to get asset.id

    # Create job referencing the asset
    job = Job(
        owner_id=owner_id,
        project_id=project_id,
        input_asset_id=asset.id,
        state="queued",
        meta={"pipeline": "local_dubbing"}
    )
    db.session.add(job)
    db.session.commit()

    # Trigger Celery task
    task = celery_app.send_task("pipeline.run_dubbing", args=[str(job.id), file_path])

    return jsonify({
        "job_id": str(job.id),
        "task_id": task.id,
        "message": "Job created successfully"
    }), 201


@job_bp.route("/status/<job_id>", methods=["GET"])
def job_status(job_id):
    """Returns job state and metadata."""
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify({
        "id": str(job.id),
        "state": job.state,
        "meta": job.meta,
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at
    }), 200
