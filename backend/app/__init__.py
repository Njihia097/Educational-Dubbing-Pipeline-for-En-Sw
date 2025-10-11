from flask import Flask
from app.config import Config
from app.database import db

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # Import and register blueprints/routes here if needed
    # from app.routes.api import api_bp
    # app.register_blueprint(api_bp)

    @app.route("/health")
    def health():
        return {"status": "ok"}, 200

    return app