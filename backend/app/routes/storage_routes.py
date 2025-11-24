# backend/app/routes/storage_routes.py
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from app.storage import storage

# This blueprint will be mounted under /api/storage in create_app
storage_bp = Blueprint("storage", __name__)


@storage_bp.get("/test")
def test_connection():
    """Simple health check to verify MinIO connectivity."""
    try:
        storage.client.list_buckets()
        return jsonify({"status": "ok", "message": "MinIO reachable"}), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@storage_bp.post("/upload")
async def upload_file():
    """Upload a file to the configured storage backend."""
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
    """List files in the underlying MinIO/S3 bucket."""
    try:
        resp = storage.client.list_objects_v2(Bucket=storage.bucket)
        files = [obj["Key"] for obj in resp.get("Contents", [])]
        return jsonify({"files": files}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@storage_bp.delete("/delete/<path:key>")
def delete_file(key):
    """Delete a file from the underlying MinIO/S3 bucket."""
    try:
        storage.delete(key)
        return jsonify({"message": f"Deleted {key} successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
