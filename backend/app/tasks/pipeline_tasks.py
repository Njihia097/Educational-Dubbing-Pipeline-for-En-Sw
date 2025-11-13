
import os, sys, datetime
from contextlib import contextmanager
from flask import current_app

from app import create_app
from app.celery_app import celery_app
from app.database import db
from app.models import Job, JobOutput, Asset
from app.services.minio_services import MinIOService

# Check for SKIP_MODEL_LOAD env to optionally skip model loading (for tests/dev)
SKIP_MODEL_LOAD = os.getenv("SKIP_MODEL_LOAD", "False").lower() == "true"

if not SKIP_MODEL_LOAD:
    from src.inference.local_pipeline.cli import init_pipeline_for_integration

# Ensure /pipeline is in sys.path for Docker
if "/pipeline" not in sys.path:
    sys.path.insert(0, "/pipeline")

# Lazy init for pipeline
_pipeline = None
def get_pipeline():
    global _pipeline
    if _pipeline is None and not SKIP_MODEL_LOAD:
        _pipeline = init_pipeline_for_integration()
    return _pipeline

# Lazy init for MinIO service
_minio_service = None
def get_minio_service():
    global _minio_service
    if _minio_service is None:
        _minio_service = MinIOService()
    return _minio_service

_worker_app = None


@contextmanager
def _app_context():
    """Provide an application context for both Flask requests and Celery workers."""
    global _worker_app
    try:
        app = current_app._get_current_object()
    except RuntimeError:
        app = None

    if app is not None:
        yield app
        return

    if _worker_app is None:
        _worker_app = create_app()

    with _worker_app.app_context():
        yield _worker_app


@celery_app.task(name="pipeline.run_dubbing")
def run_dubbing(video_path: str, job_id: str):
    """Execute dubbing pipeline and persist outputs."""
    with _app_context():
        job = db.session.get(Job, job_id)
        if not job:
            return {"status": "error", "error": f"Job {job_id} not found"}

        try:
            job.state = "running"
            job.started_at = datetime.datetime.utcnow()
            db.session.commit()

            pipeline = get_pipeline()
            result = pipeline.process(video_path, output_name=f"job_{job_id}")
            output_path = result.get("output_path")

            # Upload dubbed file to MinIO
            minio_service = get_minio_service()
            s3_url = minio_service.upload_file(output_path, object_name=f"jobs/{job_id}.mp4")

            # Register the output asset
            asset = Asset(
                owner_id=job.owner_id,
                project_id=job.project_id,
                kind="video",
                uri=s3_url,
                meta={"local_path": output_path},
            )
            db.session.add(asset)
            db.session.flush()  # obtain asset.id

            # Log as job output
            job_output = JobOutput(
                job_id=job.id,
                kind="lipsynced_video",
                asset_id=asset.id,
                meta={"s3_url": s3_url},
            )
            db.session.add(job_output)

            # Finalize job
            job.state = "succeeded"
            job.finished_at = datetime.datetime.utcnow()
            db.session.commit()

            return {"status": "success", "job_id": str(job_id), "s3_url": s3_url}

        except Exception as e:
            db.session.rollback()
            job.state = "failed"
            job.error_code = str(e)
            db.session.commit()
            return {"status": "error", "job_id": str(job_id), "error": str(e)}
