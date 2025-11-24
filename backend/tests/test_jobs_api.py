import io
import uuid
import pytest
from app import create_app
from app.database import db
from app.models.models import AppUser, Project, Job, JobStep

@pytest.fixture(scope="module")
def client():
    """
    Use the real Postgres DB (edu_pg container) for tests.
    This avoids SQLite JSONB/UUID incompatibilities.
    """
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://postgres:letsg000@postgres:5432/edu_dubbing",
        "SKIP_MODEL_LOAD": True
    })

    with app.app_context():
        # Ensure a clean DB state for tests
        db.drop_all()
        db.create_all()

        # Seed test user + project
        user = AppUser(email="test@example.com", password_hash="hashed", display_name="Tester")
        db.session.add(user)
        db.session.flush()
        project = Project(owner_id=user.id, name="Demo Project")
        db.session.add(project)
        db.session.commit()

        test_client = app.test_client()
        yield test_client, user, project

        db.session.remove()
        db.drop_all()

def test_create_job(client):
    client, user, project = client

    # Create a fake file in memory (simulate upload)
    dummy_video = io.BytesIO(b"fake video content")
    dummy_video.name = "demo.mp4"

    data = {
        "file": (dummy_video, "demo.mp4"),
        "owner_id": str(user.id),
        "project_id": str(project.id),
    }

    res = client.post("/api/jobs/create", data=data, content_type="multipart/form-data")
    assert res.status_code == 201, res.data

    payload = res.get_json()
    assert "job_id" in payload
    job_id = payload["job_id"]

    # Verify the job was created in DB
    job = db.session.get(Job, job_id)
    assert job is not None
    assert job.state == "queued"

def test_get_job_status(client):
    client, user, project = client

    # Create a dummy job directly in DB
    job = Job(owner_id=user.id, project_id=project.id, state="queued", meta={"pipeline": "local_dubbing"})
    db.session.add(job)
    db.session.commit()

    res = client.get(f"/api/jobs/status/{job.id}")
    assert res.status_code == 200
    payload = res.get_json()

    assert payload["id"] == str(job.id)
    assert payload["state"] == "queued"

def test_job_persistence(client):
    client, user, project = client

    dummy_video = io.BytesIO(b"fake content")
    dummy_video.name = "sample.mp4"
    data = {"file": (dummy_video, "sample.mp4"),
            "owner_id": str(user.id),
            "project_id": str(project.id)}

    res = client.post("/api/jobs/create", data=data, content_type="multipart/form-data")
    assert res.status_code == 201
    job_id = res.get_json()["job_id"]

    job = db.session.get(Job, job_id)
    steps = db.session.query(JobStep).filter_by(job_id=job_id).all()
    assert job is not None and len(steps) == 4

