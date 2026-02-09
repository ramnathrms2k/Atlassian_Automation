#!/usr/bin/env python3
"""
Run Jira App Resource Monitoring on a port > 9000 (default 9080).
"""
import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.flask_app import create_app
from app.config_loader import get_config

if __name__ == "__main__":
    app = create_app()
    cfg = get_config()
    port = int(os.environ.get("JIRA_MONITOR_PORT") or cfg.get("app", {}).get("port", 9080))
    if port <= 9000:
        port = 9080
    app.run(host="0.0.0.0", port=port, debug=False, threaded=True)
