# backend/app/tasks/progress_tracker.py

import datetime
from functools import wraps
from app.database import db
from app.models.models import Job, JobStep


# -----------------------------------------------------------------------------
# HELPERS — DB updates
# -----------------------------------------------------------------------------

def set_step_running(job_id: str, step: str):
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "running"
        js.started_at = datetime.datetime.utcnow()
        db.session.commit()

    job = Job.query.get(job_id)
    if job:
        job.current_step = step
        db.session.commit()


def set_step_success(job_id: str, step: str):
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "succeeded"
        js.finished_at = datetime.datetime.utcnow()
        db.session.commit()


def set_step_failed(job_id: str, step: str, error_msg: str):
    js = JobStep.query.filter_by(job_id=job_id, name=step).first()
    if js:
        js.state = "failed"
        js.finished_at = datetime.datetime.utcnow()
        js.metrics = {"error": error_msg}
        db.session.commit()

    job = Job.query.get(job_id)
    if job:
        job.state = "failed"
        job.error_code = error_msg
        job.finished_at = datetime.datetime.utcnow()
        db.session.commit()


# -----------------------------------------------------------------------------
# DECORATOR — wraps Celery task
# -----------------------------------------------------------------------------
def pipeline_step(step_name: str):
    """
    Decorator for pipeline tasks.
    Automatically:
      • extracts job_id from payload/video_s3_uri
      • marks JobStep running
      • executes task
      • marks JobStep succeeded/failed
    """

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):

            # -----------------------------------------------------------------
            # EXTRACT job_id from args
            # (task1 argument is video_s3_uri, later tasks receive payload dict)
            # -----------------------------------------------------------------
            job_id = None

            # pattern: task_asr(video_s3_uri)
            if isinstance(args[0], str) and args[0].startswith("s3://"):
                # job_id passed via Celery chain context
                job_id = self.request.chain[0]["args"][0]

            # pattern: task_xxx(payload)
            elif isinstance(args[0], dict):
                # job_id already propagated in payload
                job_id = args[0].get("job_id") or self.request.chain[0]["args"][0]

            if not job_id:
                raise RuntimeError(f"pipeline_step could not extract job_id for step '{step_name}'")

            # -----------------------------------------------------------------
            # UPDATE: Step running
            # -----------------------------------------------------------------
            set_step_running(job_id, step_name)

            try:
                # EXECUTE TASK
                result = func(self, *args, **kwargs)

                # UPDATE: Step success
                set_step_success(job_id, step_name)

                # PROPAGATE job_id inside payload for the next step
                if isinstance(result, dict):
                    result["job_id"] = job_id

                return result

            except Exception as exc:
                # UPDATE: Step failed
                set_step_failed(job_id, step_name, str(exc))
                raise

        return wrapper

    return decorator
