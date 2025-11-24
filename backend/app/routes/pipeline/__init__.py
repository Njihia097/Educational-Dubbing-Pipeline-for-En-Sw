# backend/app/routes/pipeline/__init__.py

from flask import Blueprint, jsonify, request
from celery.result import AsyncResult

pipeline_bp = Blueprint("pipeline", __name__)


@pipeline_bp.route("/run", methods=["POST"])
def start_pipeline():
    """
    Trigger the Celery dubbing pipeline.
    Expected JSON body:
    {
        "job_id": "<uuid>",
        "video_s3_uri": "s3://uploads/.../video.mp4"
    }
    """
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id")
    video_s3_uri = data.get("video_s3_uri")

    if not job_id:
        return jsonify({"error": "Missing 'job_id'"}), 400
    if not video_s3_uri:
        return jsonify({"error": "Missing 'video_s3_uri'"}), 400

    from app.tasks.pipeline_chain import queue_dubbing_chain

    task = queue_dubbing_chain(job_id, video_s3_uri)
    return (
        jsonify(
            {
                "message": "Pipeline enqueued",
                "job_id": job_id,
                "task_id": task.id,
                "video_s3_uri": video_s3_uri,
            }
        ),
        202,
    )


@pipeline_bp.route("/status/<task_id>", methods=["GET"])
def task_status(task_id):
    """Return Celery task status for a pipeline job."""
    from app.celery_app import celery_app

    result = AsyncResult(task_id, app=celery_app)
    response = {"status": result.status}
    if result.ready():
        response["result"] = result.result
    return jsonify(response)


@pipeline_bp.route("/health", methods=["GET"])
def pipeline_health():
    """Simple health endpoint for pipeline blueprint."""
    return jsonify({"status": "ready"}), 200
