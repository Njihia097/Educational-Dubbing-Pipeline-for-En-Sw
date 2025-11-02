from flask import request, jsonify
import uuid
from app.tasks.pipeline_tasks import run_dubbing
from . import pipeline_bp

@pipeline_bp.route("/run", methods=["POST"])
def start_pipeline():
    """
    Launches the full dubbing pipeline as a Celery background job.
    Expects: { "video_path": "/mnt/uploads/input.mp4" }
    """
    data = request.get_json() or {}
    video_path = data.get("video_path")

    if not video_path:
        return jsonify({"error": "Missing 'video_path' in request body"}), 400

    job_id = str(uuid.uuid4())
    task = run_dubbing.delay(video_path, job_id)
    return jsonify({
        "message": "Pipeline started",
        "job_id": job_id,
        "task_id": task.id
    }), 202
