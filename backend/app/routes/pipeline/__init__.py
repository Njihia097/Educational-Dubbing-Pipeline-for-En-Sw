from flask import Blueprint

pipeline_bp = Blueprint("pipeline", __name__)


from .run_pipeline import *  # noqa
from .task_status import *   # noqa

# Add a simple status endpoint for health checks
from flask import jsonify
@pipeline_bp.route("/status", methods=["GET"])
def pipeline_status():
	return jsonify({"status": "ready"}), 200
