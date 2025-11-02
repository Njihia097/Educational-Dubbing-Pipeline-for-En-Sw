import sys, os
# Prefer /pipeline/src in Docker, fallback to local path for local runs
if os.path.isdir("/pipeline/src"):
    src_path = "/pipeline/src"
else:
    src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../educational_dubbing_pipeline_tr/src"))
sys.path.insert(0, os.path.dirname(src_path))

# backend/tests/test_pipeline.py

import json
import uuid
import pytest

from app import create_app
from app.database import db

@pytest.fixture(scope="module")
def test_client():
    app = create_app({
        "TESTING": True,
    "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://postgres:letsg000@postgres:5432/edu_dubbing",
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        # Celery: run tasks inline so the test is deterministic
        "CELERY_TASK_ALWAYS_EAGER": True,
    })
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.drop_all()

def test_pipeline_status(test_client):
    r = test_client.get("/api/pipeline/status")
    assert r.status_code == 200
    data = r.get_json()
    assert data["status"] in {"ready", "ok"}

def test_pipeline_run(test_client, monkeypatch, tmp_path):
    # Mock the heavy pipeline so the test is fast and CI-safe
    from app.tasks.pipeline_tasks import run_dubbing

    def fake_delay(video_path, job_id):
        class R:  # minimal fake AsyncResult
            id = "fake-1"
        return R()
    monkeypatch.setattr(run_dubbing, "delay", fake_delay)

    dummy = tmp_path / "clip.mp4"
    dummy.write_bytes(b"\x00\x00\x00\x18ftypmp42")  # tiny mp4 header stub

    payload = {"video_path": str(dummy)}
    r = test_client.post("/api/pipeline/run", json=payload)
    assert r.status_code == 202, r.get_data(as_text=True)
    data = r.get_json()
    assert "job_id" in data
