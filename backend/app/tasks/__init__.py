# backend/app/tasks/__init__.py
from app.celery_app import celery_app

# Import all task modules so Celery can auto-discover them
from app.tasks import core_tasks
from app.tasks import pipeline_tasks

__all__ = ["celery_app"]
