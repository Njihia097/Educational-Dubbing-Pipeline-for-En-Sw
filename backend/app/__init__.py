# app/__init__.py
from flask import Flask
from flask_migrate import Migrate

# ✅ Use the one-and-only db instance defined in app/database.py
from app.database import db

__all__ = ["create_app"]


def create_app(config_overrides: dict | None = None):
    app = Flask(__name__)

    # Load default config, then apply test/override config BEFORE init_app.
    app.config.from_object("app.config.Config")
    if config_overrides:
        app.config.update(config_overrides)

    app.config.setdefault(
        "SQLALCHEMY_ENGINE_OPTIONS",
        {
            "pool_pre_ping": True,
            "pool_recycle": 180,
            "connect_args": {"connect_timeout": 3},
        },
    )

    db.init_app(app)
    Migrate(app, db)

    # Blueprints
    from app.routes import api_bp, storage_bp, pipeline_bp
    from app.routes.job_routes import job_bp
    from app.routes.auth_routes import auth_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(storage_bp, url_prefix="/api/storage")
    app.register_blueprint(job_bp, url_prefix="/api/jobs")
    app.register_blueprint(pipeline_bp, url_prefix="/api/pipeline")
    app.register_blueprint(auth_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
