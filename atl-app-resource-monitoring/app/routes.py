"""
Flask routes: index page and API for metrics.
"""
from flask import Blueprint, render_template, jsonify, current_app

from flask import request

from app.collector import collect_all
from app.config_loader import get_config, list_environments

bp = Blueprint("main", __name__)


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/config")
def api_config():
    """Return available environments, refresh interval, and current environment."""
    env_param = request.args.get("env")
    environments = list_environments()
    cfg = get_config(env_param)
    return jsonify({
        "environments": environments,
        "refresh_interval_seconds": cfg.get("app", {}).get("refresh_interval_seconds", 60),
        "environment": cfg.get("environment", "default"),
    })


@bp.route("/api/metrics")
def api_metrics():
    """Collect metrics from all nodes for the selected environment."""
    env_param = request.args.get("env")
    try:
        cfg = get_config(env_param)
        data = collect_all(cfg)
        return jsonify(data)
    except Exception as e:
        current_app.logger.exception("Metrics collection failed")
        return jsonify({"error": str(e), "servers": []}), 500
