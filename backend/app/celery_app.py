# backend/app/celery_app.py
from celery import Celery
import os

def make_celery():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
    celery = Celery(
        "edu_dubber",
        broker=redis_url,
        backend=redis_url,
        include=["app.tasks"]
    )
    celery.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="Africa/Nairobi",
        enable_utc=True,
    )
    return celery

celery = make_celery()
