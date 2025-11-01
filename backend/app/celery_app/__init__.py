from celery import Celery
import os

celery = Celery(
    "edu_dubber",
    broker=os.getenv("REDIS_URL", "redis://redis:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://redis:6379/0"),
)
celery.conf.update(task_track_started=True, result_expires=3600)

# Register tasks explicitly
celery.autodiscover_tasks(["app.tasks"])
