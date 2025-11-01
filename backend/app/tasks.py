# backend/app/tasks.py
import time
from app.celery_app import celery

@celery.task(name="tasks.test_task")
def test_task(n):
    """Simple demo task."""
    time.sleep(3)
    return {"message": f"Processed {n} successfully"}
