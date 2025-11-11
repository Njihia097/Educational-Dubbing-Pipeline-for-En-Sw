from flask import Blueprint, request, jsonify
from app.database import db
from app.models.models import Job, JobStep, JobOutput, Asset
from app.celery_app import celery_app
import os, uuid, datetime

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

    # Create Asset for uploaded input file
    asset = Asset(
        owner_id=owner_id,
        project_id=project_id,
        kind="video",
        uri=file_path,
        meta={"original_name": file.filename}
    )
    db.session.add(asset)
    db.session.flush()

    # Create Job
    job = Job(
        owner_id=owner_id,
        project_id=project_id,
        input_asset_id=asset.id,
        state="queued",
        meta={"pipeline": "local_dubbing"},
        created_at=datetime.datetime.utcnow(),
    )
    db.session.add(job)
    db.session.flush()

    # Initialize default JobSteps
    steps = ["asr", "translation", "tts", "lipsync"]
    for step in steps:
        db.session.add(JobStep(job_id=job.id, name=step, state="pending"))

    # Optionally initialize placeholder JobOutputs
    outputs = ["translated_text", "tts_audio", "lipsynced_video", "subtitle"]
    for output_kind in outputs:
        db.session.add(JobOutput(job_id=job.id, kind=output_kind, meta={}))

    db.session.commit()

    # Trigger Celery pipeline task
    try:
        task = celery_app.send_task("pipeline.run_dubbing", args=[str(job.id), file_path])
        return jsonify({
            "job_id": str(job.id),
            "task_id": task.id,
            "message": "Job created successfully",
            "state": job.state
        }), 201
    except Exception as e:
        job.state = "failed"
        job.error_code = str(e)
        db.session.commit()
        return jsonify({"error": f"Failed to start task: {e}"}), 500


@job_bp.route("/status/<job_id>", methods=["GET"])
def job_status(job_id):
    """Returns job state, steps, and outputs."""
    job = db.session.get(Job, job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404

    steps = db.session.query(JobStep).filter_by(job_id=job.id).all()
    outputs = db.session.query(JobOutput).filter_by(job_id=job.id).all()

    return jsonify({
        "id": str(job.id),
        "state": job.state,
        "meta": job.meta,
        "steps": [s.name for s in steps],
        "outputs": [o.kind for o in outputs],
        "created_at": job.created_at,
        "started_at": job.started_at,
        "finished_at": job.finished_at,
    }), 200
