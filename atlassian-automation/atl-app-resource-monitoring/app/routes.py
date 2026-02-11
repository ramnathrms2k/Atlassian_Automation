"""
Flask routes: index page and API for metrics.
"""
import csv
import json
from pathlib import Path

from flask import Blueprint, render_template, jsonify, current_app, request, Response

from app.collector import collect_all
from app.config_loader import get_config, list_environments

bp = Blueprint("main", __name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _monitoring_csv_path(environment: str):
    """Path to the per-environment monitoring CSV file."""
    cfg = get_config(environment)
    csv_dir = cfg.get("monitoring", {}).get("csv_directory", "data")
    path = PROJECT_ROOT / csv_dir
    path.mkdir(parents=True, exist_ok=True)
    return path / f"monitoring_{environment}.csv"


@bp.route("/")
def index():
    return render_template("index.html")


@bp.route("/api/config")
def api_config():
    """Return available environments, refresh interval, current environment, and monitoring config."""
    env_param = request.args.get("env")
    environments = list_environments()
    cfg = get_config(env_param)
    monitoring_cfg = cfg.get("monitoring") or {}
    z_score = monitoring_cfg.get("z_score") or {}
    out = {
        "environments": environments,
        "refresh_interval_seconds": cfg.get("app", {}).get("refresh_interval_seconds", 60),
        "environment": cfg.get("environment", "default"),
        "monitoring": {
            "csv_directory": monitoring_cfg.get("csv_directory", "data"),
            "csv_window_minutes": monitoring_cfg.get("csv_window_minutes", 60),
            "z_score": {
                "normal_max": z_score.get("normal_max", 1.0),
                "medium_max": z_score.get("medium_max", 2.0),
                "high_max": z_score.get("high_max", 3.0),
            },
        },
    }
    if env_param:
        out["servers"] = cfg.get("servers", [])
    return jsonify(out)


def _latest_json_path(environment: str) -> Path:
    cfg = get_config(environment)
    csv_dir = cfg.get("monitoring", {}).get("csv_directory", "data")
    p = PROJECT_ROOT / csv_dir
    return p / f"latest_{environment}.json"


@bp.route("/api/metrics")
def api_metrics():
    """Live collect (optional fallback). Prefer /api/metrics/latest for UI."""
    env_param = request.args.get("env")
    try:
        cfg = get_config(env_param)
        data = collect_all(cfg)
        return jsonify(data)
    except Exception as e:
        current_app.logger.exception("Metrics collection failed")
        return jsonify({"error": str(e), "servers": []}), 500


@bp.route("/api/metrics/latest")
def api_metrics_latest():
    """Return the latest stored snapshot for the environment (from background collection)."""
    environment = request.args.get("env")
    if not environment:
        return jsonify({"error": "env required"}), 400
    path = _latest_json_path(environment)
    if not path.exists():
        return jsonify({"error": "No latest data for this environment", "servers": []}), 404
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify(data)
    except Exception as e:
        current_app.logger.exception("Latest metrics read failed")
        return jsonify({"error": str(e), "servers": []}), 500


def _read_csv_header_and_rows(path: Path):
    if not path.exists():
        return [], []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        header = list(reader.fieldnames or [])
        rows = list(reader)
    return header, rows


@bp.route("/api/monitoring/append", methods=["POST"])
def api_monitoring_append():
    """Append one extended row to the environment's CSV. Migrates file if new columns (e.g. Apdex)."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "JSON body required"}), 400
    environment = data.get("environment")
    columns = data.get("columns")
    row = data.get("row")
    if not environment or not columns or row is None:
        return jsonify({"error": "environment, columns, and row required"}), 400
    try:
        path = _monitoring_csv_path(environment)
        existing_header, existing_rows = _read_csv_header_and_rows(path)
        new_cols = [c for c in columns if c not in existing_header]
        if not path.exists():
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(columns)
                w.writerow([row.get(c, "") for c in columns])
        elif new_cols:
            full_header = list(columns)
            with open(path, "w", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow(full_header)
                for r in existing_rows:
                    w.writerow([r.get(c, "") for c in full_header])
                w.writerow([row.get(c, "") for c in full_header])
        else:
            with open(path, "a", newline="", encoding="utf-8") as f:
                w = csv.writer(f)
                w.writerow([row.get(c, "") for c in existing_header])
        return jsonify({"ok": True, "path": str(path)})
    except Exception as e:
        current_app.logger.exception("Monitoring append failed")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/monitoring/csv")
def api_monitoring_csv():
    """Return the environment's monitoring CSV content, or 404 if not found."""
    environment = request.args.get("env")
    if not environment:
        return jsonify({"error": "env required"}), 400
    path = _monitoring_csv_path(environment)
    if not path.exists():
        return jsonify({"error": "No CSV found for this environment"}), 404
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return Response(content, mimetype="text/csv")
    except Exception as e:
        current_app.logger.exception("Monitoring CSV read failed")
        return jsonify({"error": str(e)}), 500


@bp.route("/api/monitoring/series")
def api_monitoring_series():
    """Return the environment's monitoring data as JSON { columns, rows } for charts."""
    environment = request.args.get("env")
    if not environment:
        return jsonify({"error": "env required"}), 400
    path = _monitoring_csv_path(environment)
    if not path.exists():
        return jsonify({"columns": [], "rows": []})
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames or []
            rows = list(reader)
        return jsonify({"columns": columns, "rows": rows})
    except Exception as e:
        current_app.logger.exception("Monitoring series read failed")
        return jsonify({"error": str(e)}), 500
