# backend/app/tasks/pipeline_chain.py

"""
High-level Celery workflow for the full dubbing chain.

This orchestrates:
  1) ASR
  2) punctuation
  3) MT
  4) TTS
  5) music separation + mixing
  6) final muxing
  7) output upload

All heavy ML work is done outside Docker via external_ai microservice.
"""

import datetime

from celery import shared_task, chain
from app.database import db
from app.models import Job

from .pipeline_tasks import (
    task_asr,
    task_punctuate,
    task_translate,
    task_tts,
    task_separate_music,
    task_mix,
    task_replace_audio,
)


# ============================================================================
# MAIN ENTRY TASK
# ============================================================================
@shared_task(name="pipeline.run_chain", bind=True)
def run_chain(self, job_id: str, video_s3_uri: str):
    """
    Launch the entire dubbing pipeline for a video.
    """

    job = Job.query.get(job_id)
    if not job:
        raise Exception(f"Job {job_id} not found")

    job.state = "running"
    db.session.commit()

    # Chain definition
    workflow = chain(
        task_asr.s(video_s3_uri),    # payload includes wav + video info
        task_punctuate.s(),
        task_translate.s(),
        task_tts.s(),
        task_separate_music.s(),
        task_mix.s(),
        task_replace_audio.s(),
        _finalize_job.s(job_id),
    )

    async_result = workflow.apply_async()
    return {"task_id": async_result.id, "job_id": job_id}


def queue_dubbing_chain(job_id: str, video_s3_uri: str):
    """
    Convenience wrapper used by Flask routes to enqueue the pipeline chain.
    Returns the AsyncResult so callers can grab the Celery task ID.
    """
    from app.celery_app import celery_app

    return celery_app.send_task(
        "pipeline.run_chain",
        args=(job_id, video_s3_uri),
        queue="default",
    )


@shared_task(bind=True)
def _finalize_job(self, payload: dict, job_id: str):
    job = Job.query.get(job_id)
    if not job:
        raise Exception(f"Job {job_id} not found for finalize step")

    job.state = "succeeded"
    job.current_step = "completed"
    job.progress = 100.0
    job.finished_at = datetime.datetime.utcnow()

    meta = dict(job.meta or {})
    meta["output_s3_uri"] = payload.get("output_s3_uri")
    job.meta = meta
    db.session.commit()

    payload["job_id"] = job_id
    return payload
