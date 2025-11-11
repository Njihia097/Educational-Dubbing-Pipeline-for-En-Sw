import pytest
from app import create_app
from app.database import db
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from pathlib import Path
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
