from app.celery_app import celery_app
from app.database import db
from app.models.models import Job, JobOutput, JobStep, Asset
from src.inference.local_pipeline.cli import LocalDubbingPipeline
from datetime import datetime

def update_job(job, **fields):
    """Helper to safely update job fields and commit."""
    for key, value in fields.items():
        if key == "meta":
            job.meta.update(value)  # merge JSON
        else:
            setattr(job, key, value)
    db.session.commit()

@celery_app.task(name="pipeline.run_dubbing")
def run_dubbing(job_id, file_path):
    job = db.session.get(Job, job_id)
    if not job:
        return f"Job {job_id} not found."

    update_job(job, state="running", started_at=datetime.utcnow(),
               meta={"progress": 0, "current_step": "initializing"})

    try:
        pipe = LocalDubbingPipeline()

        # Step 1: ASR
        update_job(job, meta={"progress": 25, "current_step": "ASR"})
        # (simulate ASR logic here)

        # Step 2: MT
        update_job(job, meta={"progress": 50, "current_step": "MT"})
        # (simulate translation logic here)

        # Step 3: TTS
        update_job(job, meta={"progress": 75, "current_step": "TTS"})
        # (simulate synthesis logic here)

        # Step 4: LipSync
        output_path = pipe.process(file_path)
        update_job(job, meta={"progress": 90, "current_step": "LipSync"})

        # Register final output
        output_asset = Asset(
            owner_id=job.owner_id,
            project_id=job.project_id,
            kind="video",
            uri=output_path,
            meta={"source_job": str(job.id)},
        )
        db.session.add(output_asset)
        db.session.flush()

        job_output = JobOutput(
            job_id=job.id,
            kind="lipsynced_video",
            asset_id=output_asset.id,
            meta={"path": output_path},
        )
        db.session.add(job_output)

        update_job(job, state="succeeded",
                   finished_at=datetime.utcnow(),
                   meta={"progress": 100, "current_step": "completed"})

    except Exception as e:
        update_job(job, state="failed",
                   error_code="pipeline_error",
                   meta={"error_message": str(e), "progress": 0})
        raise e

    return f"Job {job_id} completed successfully"
