
from .api import api_bp
from .storage_routes import storage_bp, test_bp

# Mount storage endpoints under the main API blueprint
api_bp.register_blueprint(storage_bp)
