# backend/app/routes/job_routes.py
from flask import Blueprint, jsonify
from app.tasks import test_task

job_bp = Blueprint("job_bp", __name__)

@job_bp.route("/run-test/<int:n>", methods=["POST"])
def run_test(n):
    task = test_task.delay(n)
    return jsonify({"task_id": task.id}), 202

@job_bp.route("/status/<task_id>")
def get_status(task_id):
    from app.celery_app import celery
    task = celery.AsyncResult(task_id)
    return jsonify({"state": task.state, "result": task.result})
