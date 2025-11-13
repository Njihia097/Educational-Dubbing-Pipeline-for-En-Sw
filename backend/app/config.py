import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Unified config ensuring external DB and sane engine defaults."""

    TESTING = os.getenv("TESTING") in ("1", "true", "True")

    SQLALCHEMY_DATABASE_URI = (
        os.getenv("SQLALCHEMY_DATABASE_URI")
        or os.getenv("DATABASE_URL")
        or "postgresql+psycopg2://postgres:letsg000@postgres:5432/edu_dubbing"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 180,
        "connect_args": {"connect_timeout": 3},
    }

    # Flask extras
    SECRET_KEY = os.getenv("JWT_SECRET", "dev-key")
    ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = ENV == "development"
