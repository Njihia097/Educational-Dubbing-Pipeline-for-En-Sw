from app.celery_app import celery_app
from app.database import db
from app.models.models import Job, JobOutput, JobStep, Asset
from src.inference.local_pipeline.cli import LocalDubbingPipeline
from datetime import datetime

@celery_app.task(name="pipeline.run_dubbing")
def run_dubbing(job_id, file_path):
    job = Job.query.get(job_id)
    if not job:
        return f"Job {job_id} not found."

    job.state = "running"
    job.started_at = datetime.utcnow()
    db.session.commit()

    try:
        # Initialize and run pipeline
        pipe = LocalDubbingPipeline()
        output_path = pipe.process(file_path)

        # Register output as new Asset
        output_asset = Asset(
            owner_id=job.owner_id,
            project_id=job.project_id,
            kind="video",
            uri=output_path,
            meta={"source_job": str(job.id)}
        )
        db.session.add(output_asset)

        # Record JobOutput link
        job_output = JobOutput(
            job_id=job.id,
            kind="lipsynced_video",
            asset_id=output_asset.id,
            meta={"path": output_path}
        )
        db.session.add(job_output)

        # Update job state
        job.state = "succeeded"
        job.finished_at = datetime.utcnow()
        db.session.commit()

    except Exception as e:
        job.state = "failed"
        job.error_code = str(e)
        job.finished_at = datetime.utcnow()
        db.session.commit()
        raise e

    return f"Job {job_id} completed successfully"
