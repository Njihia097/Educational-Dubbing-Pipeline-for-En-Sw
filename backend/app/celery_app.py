# backend/app/celery_app.py
from celery import Celery
import os
    
def make_celery():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    celery = Celery(
        __name__,
        broker=redis_url,
        backend=redis_url
    )
    celery.conf.update(
        task_routes={
            "tasks.test_task": {"queue": "default"},
            "pipeline.run_dubbing": {"queue": "gpu"},
        },
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
    )
    return celery

# Explicit Celery instance name for import consistency
celery_app = make_celery()

