from flask import jsonify
from celery.result import AsyncResult
from app import celery_app
from . import pipeline_bp

@pipeline_bp.route("/status/<task_id>", methods=["GET"])
def task_status(task_id):
    """
    Returns the current status and result of a given Celery task.
    """
    result = AsyncResult(task_id, app=celery_app)
    response = {"status": result.status}

    if result.ready():
        response["result"] = result.result

    return jsonify(response)
