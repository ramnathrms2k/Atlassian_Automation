"""
Flask application factory for Jira App Resource Monitoring.
"""
import threading
from pathlib import Path

from flask import Flask

from app.config_loader import get_config, list_environments
from app.routes import bp as main_bp
from app.background import start_scheduler


def create_app():
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates",
        instance_relative_config=True,
    )
    app.config["JSONIFY_PRETTYPRINT_REGULAR"] = True
    root = Path(__file__).resolve().parent.parent
    app.template_folder = str(root / "templates")
    app.static_folder = str(root / "static")
    app.register_blueprint(main_bp)

    cfg = get_config()
    monitoring = cfg.get("monitoring") or {}
    background_envs = monitoring.get("background_environments")
    if not background_envs:
        background_envs = list_environments()
    interval_sec = int(monitoring.get("interval_seconds") or 60)
    if background_envs:
        thread = threading.Thread(
            target=start_scheduler,
            args=(interval_sec, background_envs),
            daemon=True,
        )
        thread.start()

    return app
