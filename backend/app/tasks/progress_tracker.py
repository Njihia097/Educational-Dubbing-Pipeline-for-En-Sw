# backend/app/tasks/progress_tracker.py

import datetime
from functools import wraps

from app.database import db
from app.models.models import Job, JobStep


# ---------------------------------------------------------------------
# HELPERS — DB updates
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
    """
    Final failure — no more retries.
    Marks step + job as failed.
    """
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
    """
    Retry in progress for a specific step.
    Keeps job.state = 'running', but:
      • marks step as 'retrying'
      • increments retry counters
      • records last error
    """
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "retrying"
        js.finished_at = None  # still in-flight
        js.retry_count = (js.retry_count or 0) + 1

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
# DECORATOR — wraps Celery task with retry logic
# ---------------------------------------------------------------------
def pipeline_step(step_name: str, max_retries: int = 3, backoff_seconds: int = 10):
    """
    Decorator for pipeline tasks.

    Responsibilities:
      • Extract job_id from chain payload
      • Mark JobStep 'running'
      • On success → mark 'succeeded'
      • On failure
          - If retries < max_retries: mark 'retrying' and self.retry()
          - Else: mark 'failed' and propagate error
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            # -------------------------------------------------------------
            # Extract job_id from args / Celery chain
            # -------------------------------------------------------------
            job_id = None

            # 1) First task: task_asr(video_s3_uri : str)
            if args and isinstance(args[0], str) and args[0].startswith("s3://"):
                # job_id is the first arg in the root chain
                try:
                    job_id = self.request.chain[0]["args"][0]
                except Exception:
                    raise RuntimeError(
                        f"pipeline_step(asr) could not resolve job_id from Celery chain for step '{step_name}'"
                    )

            # 2) Later tasks: task_xxx(payload : dict)
            elif args and isinstance(args[0], dict):
                payload = args[0]
                job_id = payload.get("job_id")
                if not job_id:
                    # fallback to root chain arg
                    try:
                        job_id = self.request.chain[0]["args"][0]
                    except Exception:
                        raise RuntimeError(
                            f"pipeline_step could not extract job_id for step '{step_name}'"
                        )

            if not job_id:
                raise RuntimeError(f"pipeline_step could not extract job_id for step '{step_name}'")

            # -------------------------------------------------------------
            # Mark step as running
            # -------------------------------------------------------------
            set_step_running(job_id, step_name)

            try:
                # EXECUTE TASK BODY
                result = func(self, *args, **kwargs)

                # On success, mark step succeeded
                set_step_success(job_id, step_name)

                # Propagate job_id in payload for next step in chain
                if isinstance(result, dict):
                    result["job_id"] = job_id

                return result

            except Exception as exc:
                # ---------------------------------------------------------
                # RETRY HANDLING
                # ---------------------------------------------------------
                current_retries = getattr(self.request, "retries", 0)

                if current_retries < max_retries:
                    # Mark DB as "retrying" and increment counters
                    set_step_retry(job_id, step_name, str(exc))

                    # Exponential backoff: base * 2^retries
                    countdown = backoff_seconds * (2 ** current_retries)

                    # Schedule Celery retry (this raises a Retry exception)
                    raise self.retry(
                        exc=exc,
                        countdown=countdown,
                        max_retries=max_retries,
                    )

                # ---------------------------------------------------------
                # MAX RETRIES REACHED → FINAL FAILURE
                # ---------------------------------------------------------
                set_step_failed(job_id, step_name, str(exc))
                raise

        return wrapper

    return decorator
