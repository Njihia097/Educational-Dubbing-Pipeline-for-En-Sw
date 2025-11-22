# backend/app/tasks/pipeline_chain.py

"""
High-level Celery workflow for the full dubbing chain.

NEW (Option A):
  - We now use a single external_ai /full call via task_full_chain.
  - JobSteps for the classic stages (asr, punctuate, translate, tts,
    separate_music, mix, replace_audio) are still created so the
    dashboard remains compatible. _finalize_job marks them all as
    succeeded once the full chain completes.
"""

import datetime
from celery import shared_task, chain
from app.database import db
from app.models.models import Job, JobStep
from app.tasks.progress_tracker import set_step_success

from .pipeline_tasks import (
    task_full_chain,  # 👈 NEW single-call task
)


# The logical pipeline stages we still expose to the UI
PIPELINE_STEPS = [
    "asr",
    "punctuate",
    "translate",
    "tts",
    "separate_music",
    "mix",
    "replace_audio",
]


# ============================================================================
# MAIN ENTRY TASK
# ============================================================================
@shared_task(name="pipeline.run_chain", bind=True)
def run_chain(self, job_id: str, video_s3_uri: str):
    """
    Launch the entire dubbing pipeline for a video.

    Implementation:
      • Create JobStep rows for all stages (for UI compatibility)
      • Run a SINGLE Celery task (task_full_chain) that calls /full
      • Finalize job & mark all steps as succeeded in _finalize_job
    """

    job = Job.query.get(job_id)
    if not job:
        raise Exception(f"Job {job_id} not found")

    # Mark job running
    job.state = "running"
    job.started_at = datetime.datetime.utcnow()
    db.session.commit()

    # ----------------------------------------------------------------------
    # Ensure JobStep entries exist (one per pipeline logical stage)
    # ----------------------------------------------------------------------
    existing = {s.name for s in JobStep.query.filter_by(job_id=job_id).all()}
    for step in PIPELINE_STEPS:
        if step not in existing:
            db.session.add(JobStep(job_id=job_id, name=step, state="pending"))
    db.session.commit()

    # ----------------------------------------------------------------------
    # Chain definition: single full-chain task + finalizer
    # ----------------------------------------------------------------------
    workflow = chain(
        task_full_chain.s(video_s3_uri),
        _finalize_job.s(job_id),
    )

    async_result = workflow.apply_async()
    return {"task_id": async_result.id, "job_id": job_id}


def queue_dubbing_chain(job_id: str, video_s3_uri: str):
    """
    Called by Flask route /jobs/create.
    """
    from app.celery_app import celery_app

    return celery_app.send_task(
        "pipeline.run_chain",
        args=(job_id, video_s3_uri),
        queue="default",
    )


# ============================================================================
# FINALIZER
# ============================================================================
@shared_task(bind=True)
def _finalize_job(self, payload: dict, job_id: str):

    # Mark all logical pipeline steps as successful for this job
    for step_name in PIPELINE_STEPS:
        set_step_success(job_id, step_name)

    job = Job.query.get(job_id)
    if not job:
        raise Exception(f"Job {job_id} not found for finalize step")

    job.state = "succeeded"
    job.current_step = "completed"
    job.progress = 100.0
    job.finished_at = datetime.datetime.utcnow()

    meta = dict(job.meta or {})
    # propagate output_s3_uri from payload
    if payload.get("output_s3_uri"):
        meta["output_s3_uri"] = payload.get("output_s3_uri")
    # Store transcriptions and translations (both plain text and timestamped segments)
    if payload.get("english"):
        meta["english"] = payload.get("english")
    if payload.get("swahili"):
        meta["swahili"] = payload.get("swahili")
    if payload.get("english_segments"):
        meta["english_segments"] = payload.get("english_segments")
    if payload.get("swahili_segments"):
        meta["swahili_segments"] = payload.get("swahili_segments")
    job.meta = meta

    db.session.commit()

    payload["job_id"] = job_id
    return payload
