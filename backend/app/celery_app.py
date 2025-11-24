# backend/app/celery_app.py
import os
from celery import Celery
from kombu import Queue

_flask_app = None
_ROLE = os.getenv("ROLE", "backend").lower()


def _get_flask_app():
    """
    Lazily create the Flask app (ONLY when running inside worker).

    This avoids circular imports when Celery bootstraps:
      celery → app.celery_app → _get_flask_app() → create_app() → routes
    Routes themselves no longer import Celery or tasks, so this is safe.
    """
    global _flask_app
    if _flask_app is None and _ROLE == "worker":
        from app import create_app
        _flask_app = create_app()
    return _flask_app


def make_celery() -> Celery:
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

    app = Celery(
        __name__,
        broker=redis_url,
        backend=redis_url,
    )

    # Declare Celery task modules (string paths only)
    app.conf.imports = (
        "app.tasks.pipeline_tasks",
        "app.tasks.pipeline_chain",
    )

    app.conf.update(
        task_routes={
            "pipeline.run_chain": {"queue": "default"},
        },
        task_default_queue="default",
        task_default_exchange="default",
        task_default_routing_key="default",
        task_queues=(Queue("default"),),
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        worker_prefetch_multiplier=int(os.getenv("CELERYD_PREFETCH_MULTIPLIER", "1")),
        task_acks_late=os.getenv("CELERY_ACKS_LATE", "true").lower() == "true",
        worker_max_tasks_per_child=int(os.getenv("CELERY_MAX_TASKS_PER_CHILD", "10")),
        task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800")),
        task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "1500")),
        result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),
    )

    flask_app = _get_flask_app()
    TaskBase = app.Task

    class ContextTask(TaskBase):
        """Ensure tasks execute inside Flask app context when available."""
        def __call__(self, *args, **kwargs):
            if flask_app is None:
                return TaskBase.__call__(self, *args, **kwargs)
            with flask_app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    app.Task = ContextTask
    return app


celery_app = make_celery()
