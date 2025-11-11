from flask import Blueprint, request, jsonify
from app.database import db
from app.models.models import Job, JobStep, JobOutput, Asset
from app.celery_app import celery_app
from app.utils.minio_client import upload_file
import os, uuid, datetime

job_bp = Blueprint("job_bp", __name__)

@job_bp.route("/create", methods=["POST"])
def create_job():
    file = request.files.get("file")
    owner_id = request.form.get("owner_id")
    project_id = request.form.get("project_id")

    if not file or not owner_id:
        return jsonify({"error": "Missing file or owner_id"}), 400

    # Save temporarily before MinIO upload
    temp_path = f"/tmp/{uuid.uuid4()}_{file.filename}"
    file.save(temp_path)

    # Upload to MinIO
    bucket = os.getenv("MINIO_BUCKET_UPLOADS", "uploads")
    object_name = f"{owner_id}/{uuid.uuid4()}_{file.filename}"
    s3_uri = upload_file(bucket, object_name, temp_path)

    # Remove temp file
    if os.path.exists(temp_path):
        os.remove(temp_path)

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

