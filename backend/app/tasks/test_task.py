from app.celery_app import celery
import time

@celery.task(name="tasks.test_task")
def test_task(duration=5):
    """Simulates a background job that takes a few seconds."""
    print(f"🧩 Running test task for {duration} seconds...")
    time.sleep(duration)
    print("✅ Test task completed!")
    return f"Task completed in {duration} seconds"
