from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config import Config
from app.database import db
from flask_migrate import Migrate

db = SQLAlchemy()


def create_app():
    app = Flask(__name__)
    app.config.from_object("app.config.Config")
    db.init_app(app)

    Migrate(app, db)

    # Import and register blueprints/routes here if needed
    # from app.routes.api import api_bp
    # app.register_blueprint(api_bp)

    # @app.route("/health")
    # def health():
    #     return {"status": "ok"}, 200

    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    return app