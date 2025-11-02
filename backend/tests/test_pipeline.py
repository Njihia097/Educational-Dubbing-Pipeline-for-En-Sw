import sys, os
# Prefer /pipeline/src in Docker, fallback to local path for local runs
if os.path.isdir("/pipeline/src"):
    src_path = "/pipeline/src"
else:
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../educational_dubbing_pipeline_tr/src"))
sys.path.insert(0, os.path.dirname(src_path))
# backend/tests/test_pipeline.py
import pytest
from unittest.mock import patch

@pytest.fixture
def client():
    from app import create_app
    app = create_app()
    app.testing = True
    with app.test_client() as client:
        yield client

@patch("app.tasks.pipeline_tasks.run_dubbing.delay")
def test_pipeline_run(mock_task, client):
    """Ensure POST /api/pipeline/run queues a task."""
    mock_task.return_value.id = "mock-task-id"
    response = client.post(
        "/api/pipeline/run",
        json={"video_path": "/tmp/sample.mp4"}
    )
    assert response.status_code == 202
    data = response.get_json()
    assert "job_id" in data
    assert data["task_id"] == "mock-task-id"

@patch("app.routes.pipeline.task_status.AsyncResult")
def test_pipeline_status(mock_result, client):
    """Ensure GET /api/pipeline/status/<id> returns mock status."""
    mock_result.return_value.status = "SUCCESS"
    mock_result.return_value.ready.return_value = True
    mock_result.return_value.result = {"status": "success"}

    response = client.get("/api/pipeline/status/mock-task-id")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "SUCCESS"
    assert data["result"]["status"] == "success"
