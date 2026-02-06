"""
Flask application factory for Jira App Resource Monitoring.
"""
import os
from pathlib import Path

from flask import Flask

from app.routes import bp as main_bp


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
    return app
