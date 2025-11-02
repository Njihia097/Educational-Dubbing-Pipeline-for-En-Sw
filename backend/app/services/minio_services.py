# app/services/minio_service.py
import os
from datetime import timedelta
from minio import Minio


class MinIOService:
    """Helper for simplified uploads + presigned URL generation."""
    def __init__(self):
        endpoint = os.getenv("S3_ENDPOINT", "http://minio:9000")
        endpoint = endpoint.replace("http://", "").replace("https://", "")
        self.client = Minio(
            endpoint,
            access_key=os.getenv("S3_ACCESS_KEY"),
            secret_key=os.getenv("S3_SECRET_KEY"),
            secure=os.getenv("S3_SECURE", "False").lower() == "true",
        )
        self.bucket = os.getenv("S3_BUCKET", "edu-dubbing")

        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, local_path, object_name=None):
        """Upload file and return a 7-day signed URL."""
        object_name = object_name or os.path.basename(local_path)
        self.client.fput_object(self.bucket, object_name, local_path)
        return self.client.presigned_get_object(
            self.bucket, object_name, expires=timedelta(days=7)
        )
