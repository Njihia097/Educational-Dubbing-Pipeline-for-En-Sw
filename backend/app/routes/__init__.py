# backend/app/routes/__init__.py

from . import job_routes  # re-exported for tests that patch functions
from .api import api_bp
from .storage_routes import storage_bp
from .pipeline import pipeline_bp

__all__ = ["api_bp", "storage_bp", "pipeline_bp", "job_routes"]
