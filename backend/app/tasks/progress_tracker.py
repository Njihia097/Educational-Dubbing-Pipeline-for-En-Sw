# backend/app/tasks/progress_tracker.py

import datetime
from functools import wraps

from app.database import db
from app.models.models import Job, JobStep


# ---------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------
def _now():
    return datetime.datetime.utcnow()


def set_step_running(job_id: str, step: str):
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "running"
        js.started_at = _now()
        db.session.commit()

    job = Job.query.get(job_id)
    if job:
        job.current_step = step
        job.state = "running"
        db.session.commit()


def set_step_success(job_id: str, step: str):
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "succeeded"
        js.finished_at = _now()
        db.session.commit()


def set_step_failed(job_id: str, step: str, error_msg: str):
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "failed"
        js.finished_at = _now()
        metrics = dict(js.metrics or {})
        metrics["error"] = error_msg
        metrics["failed_at"] = _now().isoformat()
        js.metrics = metrics
        db.session.commit()

    job = Job.query.get(job_id)
    if job:
        job.state = "failed"
        job.error_code = error_msg
        job.last_error_message = error_msg
        job.finished_at = _now()
        db.session.commit()


def set_step_retry(job_id: str, step: str, error_msg: str):
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "retrying"
        js.retry_count = (js.retry_count or 0) + 1
        js.finished_at = None

        metrics = dict(js.metrics or {})
        metrics["last_error"] = error_msg
        metrics["last_retry_at"] = _now().isoformat()
        js.metrics = metrics
        db.session.commit()

    job = Job.query.get(job_id)
    if job:
        job.retry_count = (job.retry_count or 0) + 1
        job.last_error_message = error_msg
        db.session.commit()


# ---------------------------------------------------------------------
# NEW DECORATOR (Option A compatible)
# ---------------------------------------------------------------------
def pipeline_step(step_name: str, max_retries: int = 3, backoff_seconds: int = 10):
    """
    Option A aware:
      • Only task_full_chain actively runs pipeline logic.
      • Other "steps" are virtual and marked in finalizer.
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):

            # ---------------------------------------------------------
            # JOB ID extraction (new logic)
            # ---------------------------------------------------------
            job_id = None

            # From payload dict
            if args and isinstance(args[0], dict):
                job_id = args[0].get("job_id")

            # From chain metadata (Celery)
            if not job_id:
                try:
                    job_id = self.request.chain[0]["args"][0]
                except Exception:
                    pass

            if not job_id:
                raise RuntimeError(
                    f"pipeline_step could not resolve job_id for step '{step_name}'"
                )

            # ---------------------------------------------------------
            # ONLY FIRST STEP should be marked in Option A
            # task_full_chain is decorated as ("asr")
            # ---------------------------------------------------------
            set_step_running(job_id, step_name)

            try:
                result = func(self, *args, **kwargs)

                # task_full_chain only marks asr as succeeded
                set_step_success(job_id, step_name)

                if isinstance(result, dict):
                    result["job_id"] = job_id

                return result

            except Exception as exc:
                # Retry logic identical to old version
                current_retries = getattr(self.request, "retries", 0)

                if current_retries < max_retries:
                    set_step_retry(job_id, step_name, str(exc))
                    countdown = backoff_seconds * (2 ** current_retries)
                    raise self.retry(
                        exc=exc,
                        countdown=countdown,
                        max_retries=max_retries,
                    )

                # Final failure
                set_step_failed(job_id, step_name, str(exc))
                raise

        return wrapper

    return decorator
