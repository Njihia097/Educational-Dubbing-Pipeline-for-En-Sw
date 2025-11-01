import os
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from app.storage import storage
from app.tasks import test_task

# This blueprint is mounted under the API blueprint at /api
storage_bp = Blueprint("storage", __name__, url_prefix="/storage")

@storage_bp.get("/test")
def test_connection():
    try:
        # List buckets to verify connectivity
        storage.client.list_buckets()
        return jsonify({"status": "ok", "message": "MinIO reachable"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@storage_bp.post("/upload")
async def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files["file"]
    filename = secure_filename(file.filename)

    try:
        data = file.read()
        url = storage.put(filename, data, file.content_type)
        return jsonify({"message": "Upload successful", "url": url}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@storage_bp.get("/list")
def list_files():
    try:
        resp = storage.client.list_objects_v2(Bucket=storage.bucket)
        files = [obj["Key"] for obj in resp.get("Contents", [])]
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@storage_bp.delete("/delete/<path:key>")
def delete_file(key):
    try:
        storage.delete(key)
        return jsonify({"message": f"Deleted {key} successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    

test_bp = Blueprint("test_bp", __name__)

@test_bp.route("/api/test_task", methods=["POST"])
def trigger_test_task():
    """Endpoint to trigger background test task."""
    task = test_task.delay(5)
    return jsonify({"task_id": task.id}), 202
