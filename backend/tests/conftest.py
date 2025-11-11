import pytest
from unittest.mock import patch
from app import create_app
from app.database import db
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from pathlib import Path
from app.models.models import AppUser, Project
import os

from huggingface_hub import constants  # ✅ correct import

os.environ["HF_HOME"] = "/tmp/hf_cache/huggingface"
os.environ["HF_HUB_CACHE"] = "/tmp/hf_cache/huggingface"
os.environ["TRANSFORMERS_CACHE"] = "/tmp/hf_cache/huggingface/transformers"

constants.HF_TOKEN_PATH = Path("/tmp/hf_cache/huggingface/token")
constants.HF_CACHE_HOME = Path("/tmp/hf_cache/huggingface")
constants.HF_HUB_CACHE = Path("/tmp/hf_cache/huggingface")

os.environ.setdefault("FLASK_ENV", "testing")

@pytest.fixture(scope="session")
def app():
    """Create one app + database for all tests."""
    app = create_app()
    app.config.update({
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "TESTING": True,
        "SKIP_MODEL_LOAD": True,
    })

    with app.app_context():
        db.create_all()
        try:
            yield app
        finally:
            db.session.remove()
            db.drop_all()


@pytest.fixture(scope="function", autouse=True)
def session_transaction(app):
    """Provide a nested transaction per test and rollback after."""
    connection = db.engine.connect()
    transaction = connection.begin()

    # Bind a new session
    Session = sessionmaker(bind=connection)
    session = Session()
    original_session = db.session
    db.session = session

    try:
        yield session
    finally:
        transaction.rollback()
        session.close()
        db.session = original_session
        connection.close()

@pytest.fixture(scope="module")
def client():
    """Test client with Celery mocked to avoid real async jobs."""
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "postgresql+psycopg2://postgres:letsg000@postgres:5432/edu_dubbing",
        "SKIP_MODEL_LOAD": True,
    })

    with app.app_context():
        db.drop_all()
        db.create_all()

        user = AppUser(email="test@example.com", password_hash="hashed", display_name="Tester")
        db.session.add(user)
        db.session.flush()
        project = Project(owner_id=user.id, name="Demo Project")
        db.session.add(project)
        db.session.commit()

        test_client = app.test_client()

        # Mock Celery task delay so it doesn’t execute heavy pipelines
        with patch("app.routes.jobs.start_dubbing_task.delay") as mock_delay:
            mock_delay.return_value = None
            yield test_client, user, project

        db.session.remove()
        db.drop_all()
