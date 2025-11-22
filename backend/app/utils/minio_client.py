# backend/app/utils/minio_client.py
import logging
import os
from datetime import timedelta
from urllib.parse import urlparse

from minio import Minio

logger = logging.getLogger(__name__)


def get_minio_client() -> Minio:
    endpoint = os.getenv("S3_ENDPOINT")
    access_key = os.getenv("S3_ACCESS_KEY")
    secret_key = os.getenv("S3_SECRET_KEY")
    secure = os.getenv("S3_SECURE", "False").lower() == "true"

    if not all([endpoint, access_key, secret_key]):
        raise EnvironmentError(
            "❌ Missing one or more required MinIO environment variables: "
            "S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY"
        )

    endpoint = endpoint.replace("http://", "").replace("https://", "").strip("/")

    return Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)


def ensure_bucket(bucket_name: str):
    client = get_minio_client()
    if not client.bucket_exists(bucket_name):
        logger.info("Creating MinIO bucket %s", bucket_name)
        client.make_bucket(bucket_name)
    return client


def upload_file(bucket: str, object_name: str, file_path: str) -> str:
    client = ensure_bucket(bucket)

    from mimetypes import guess_type
    ctype = guess_type(file_path)[0] or "application/octet-stream"

    logger.info(f"Uploading {object_name} to bucket {bucket} (ctype={ctype})")

    client.fput_object(
        bucket,
        object_name,
        file_path,
        content_type=ctype
    )

    return f"s3://{bucket}/{object_name}"


def download_file(bucket: str, object_name: str, file_path: str) -> str:
    client = get_minio_client()
    logger.info("Downloading %s from bucket %s -> %s", object_name, bucket, file_path)
    client.fget_object(bucket, object_name, file_path)
    return file_path


def presign_url(bucket, object_name, expires_in=3600, extra_headers=None):
    public_host = os.getenv("PUBLIC_MINIO_HOST")
    if public_host:
        parsed = urlparse(public_host)
        endpoint = parsed.netloc
        secure = parsed.scheme == "https"
        access_key = os.getenv("S3_ACCESS_KEY")
        secret_key = os.getenv("S3_SECRET_KEY")
        client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
    else:
        client = get_minio_client()

    return client.presigned_get_object(
        bucket,
        object_name,
        expires=timedelta(seconds=expires_in),
        response_headers=extra_headers or {}
    )


