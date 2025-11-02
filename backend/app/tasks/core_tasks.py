# backend/app/tasks/core_tasks.py
from app.celery_app import celery_app

@celery_app.task(name="tasks.test_task")
def test_task(x=5):
    return {"message": f"Processed {x} successfully"}
