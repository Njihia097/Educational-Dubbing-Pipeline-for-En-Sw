"""Utilities for downloading MinIO objects to local temp files."""
from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import urlparse

from app.utils.minio_client import get_minio_client


TEMP_ROOT = Path("/tmp/pipeline_inputs")


def download_minio_uri(uri: str) -> str:
    """
    Download an s3://bucket/path/file.ext object to a local temp path.
    Returns the absolute local filesystem path.
    """
    parsed = urlparse(uri)
    if parsed.scheme.lower() != "s3":
        raise ValueError(f"Unsupported URI scheme for download: {uri}")

    bucket = parsed.netloc
    object_name = parsed.path.lstrip("/")
    if not bucket or not object_name:
        raise ValueError(f"Invalid S3 URI: {uri}")

    suffix = Path(object_name).suffix or ".bin"
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
    local_path = TEMP_ROOT / f"{uuid.uuid4()}{suffix}"

    print(f"[MINIO] Downloading {uri} → {local_path}")
    client = get_minio_client()
    try:
        client.fget_object(bucket, object_name, str(local_path))
    except Exception as exc:  # pragma: no cover - defensive
        if local_path.exists():
            local_path.unlink(missing_ok=True)
        print(f"[MINIO] ERROR: {exc}")
        raise

    if not local_path.exists():
        raise ValueError(f"Download failed, file missing at {local_path}")
    size = local_path.stat().st_size
    if size == 0:
        local_path.unlink(missing_ok=True)
        raise ValueError(f"Downloaded file is empty: {uri}")

    print(f"[MINIO] Download complete: {local_path} ({size} bytes)")
    return str(local_path)
