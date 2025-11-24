from app import create_app
import os

app = create_app()

if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", "5000"))
    debug = str(os.getenv("FLASK_DEBUG", "1")).lower() in ("1", "true", "yes")
    app.run(host=host, port=port, debug=debug)

# $env:S3_ENDPOINT='http://localhost:9000'; python run.py).
