# backend/app/tasks/pipeline_tasks.py
import os, sys
# With PYTHONPATH set, you usually don't need these, but keeping /pipeline is harmless:
if "/pipeline" not in sys.path:
    sys.path.insert(0, "/pipeline")

from app.celery_app import celery_app
from src.inference.local_pipeline.cli import init_pipeline_for_integration

# 🌟 Lazy init to avoid loading heavy models during Flask CLI/migrations
_pipeline = None
def get_pipeline():
    global _pipeline
    if _pipeline is None:
        _pipeline = init_pipeline_for_integration()
    return _pipeline

@celery_app.task(name="pipeline.run_dubbing")
def run_dubbing(video_path: str, job_id: str):
    try:
        pipe = get_pipeline()
        result = pipe.process(video_path, output_name=f"job_{job_id}")
        return {"status": "success", "job_id": job_id, "output": result}
    except Exception as e:
        return {"status": "error", "job_id": job_id, "error": str(e)}
