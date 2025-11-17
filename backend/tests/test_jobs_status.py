import io
import os
from datetime import datetime, timezone
from types import SimpleNamespace

from app.database import db
from app.models.models import AppUser, Job, Project, JobOutput, JobStep, Asset


def _create_user(email="progress@test.com"):
    user = AppUser(email=email, password_hash="x")
    db.session.add(user)
    db.session.commit()
    return user


def _create_project(owner_id, name="Demo Project"):
    project = Project(owner_id=owner_id, name=name)
    db.session.add(project)
    db.session.commit()
    return project


def test_job_progress_polling(app):
    client = app.test_client()
    user = _create_user()

    job = Job(
        owner_id=user.id,
        state="running",
        meta={"progress": 50.0, "current_step": "TTS"},
        created_at=datetime.now(timezone.utc),
    )
    db.session.add(job)
    db.session.commit()
    job_id = str(job.id)

    res = client.get(f"/api/jobs/status/{job_id}")
    data = res.get_json()
    assert res.status_code == 200
    assert data["meta"]["progress"] == 50.0
    assert data["meta"]["current_step"] == "TTS"


def test_create_job_enqueues_pipeline(app, monkeypatch):
    client = app.test_client()
    user = _create_user("pipeline@test.com")
    project = _create_project(user.id, "Pipeline Project")

    from app.routes import job_routes

    bucket_name = os.getenv("MINIO_BUCKET_UPLOADS", "uploads")
    calls = {}

    def fake_upload(bucket, object_name, file_path):
        assert os.path.exists(file_path)
        calls["upload"] = (bucket, object_name)
        return f"s3://{bucket}/{object_name}"

    class DummyTask:
        id = "task-123"

    def fake_queue(job_id, s3_uri):
        calls["task"] = (job_id, s3_uri)
        return DummyTask()

    monkeypatch.setattr(job_routes, "upload_file", fake_upload)
    monkeypatch.setattr(job_routes, "queue_dubbing_chain", fake_queue)

    data = {
        "file": (io.BytesIO(b"fake video"), "sample.mp4"),
        "owner_id": str(user.id),
        "project_id": str(project.id),
    }

    res = client.post("/api/jobs/create", data=data, content_type="multipart/form-data")
    assert res.status_code == 201
    payload = res.get_json()

    job_id = payload["job_id"]
    job = db.session.get(Job, job_id)
    assert job is not None
    assert job.state == "queued"
    assert job.input_asset_id is not None

    asset = db.session.get(Asset, job.input_asset_id)
    assert asset is not None
    assert asset.uri.startswith(f"s3://{bucket_name}/")

    steps = JobStep.query.filter_by(job_id=job_id).all()
    assert len(steps) == 4
    assert {s.name for s in steps} == {"asr", "translation", "tts", "lipsync"}

    outputs = JobOutput.query.filter_by(job_id=job_id).all()
    assert len(outputs) == 4

    assert calls["upload"][0] == bucket_name
    assert calls["task"][0] == str(job.id)
    assert calls["task"][1].startswith(f"s3://{bucket_name}/")
