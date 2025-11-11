# backend/app/celery_app.py
from celery import Celery
import os
    
def make_celery():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    app = Celery(
        __name__,
        broker=redis_url,
        backend=redis_url
    )
    app.conf.update(
        # Ensure task modules are loaded
        imports=[
            "app.tasks.test_task",
            "app.tasks.pipeline_tasks",
        ],
        task_routes={
            "tasks.test_task": {"queue": "default"},
            "pipeline.run_dubbing": {"queue": "gpu"},
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        # Throughput / fairness
        worker_prefetch_multiplier=int(os.getenv("CELERYD_PREFETCH_MULTIPLIER", "1")),
        task_acks_late=os.getenv("CELERY_ACKS_LATE", "true").lower() == "true",
        worker_max_tasks_per_child=int(os.getenv("CELERY_MAX_TASKS_PER_CHILD", "10")),
        # Reasonable limits to avoid stuck workers
        task_time_limit=int(os.getenv("CELERY_TASK_TIME_LIMIT", "1800")),      # 30m
        task_soft_time_limit=int(os.getenv("CELERY_TASK_SOFT_TIME_LIMIT", "1500")),
        # Lighter backend
        result_expires=int(os.getenv("CELERY_RESULT_EXPIRES", "3600")),
    )
    return app

# Explicit Celery instance name for import consistency
celery_app = make_celery()

