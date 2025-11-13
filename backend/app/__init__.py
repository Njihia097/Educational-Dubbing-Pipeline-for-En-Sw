# app/__init__.py
from flask import Flask
from flask_migrate import Migrate

# ✅ Use the one-and-only db instance defined in app/database.py
from app.database import db
from app.celery_app import celery_app  # re-export for modules using `from app import celery_app`

__all__ = ["create_app", "celery_app"]


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
    from app.routes import api_bp, test_bp
    from app.routes.job_routes import job_bp
    from app.routes.pipeline import pipeline_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(job_bp, url_prefix="/api/jobs")
    app.register_blueprint(test_bp)
    app.register_blueprint(pipeline_bp, url_prefix="/api/pipeline")

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app
