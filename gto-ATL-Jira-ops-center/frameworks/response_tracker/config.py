# config.py
# Adapted for config injection from instances_config

import sys
import os

# Try to get injected config from parent
_injected_config = None

def inject_config(config):
    """Inject instance configuration."""
    global _injected_config
    _injected_config = config

def get_injected_config():
    """Get injected configuration."""
    return _injected_config

# Get injected config if available
try:
    # Try to import from parent config_manager
    parent_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, parent_dir)
    from config_manager import get_injected_config as _get_injected
    _injected_config = _get_injected('response-tracker')
except:
    pass

# Use injected config if available, otherwise use defaults
if _injected_config:
    instance_config = _injected_config
    
    # Jira Server Configuration
    JIRA_SERVERS = [
        {
            "name": server["name"],
            "hostname": server["hostname"],
            "log_path": server.get("log_path", "/export/jira/logs")
        }
        for server in instance_config.get("jira_servers", [])
    ]
    
    # SSH Configuration
    ssh = instance_config.get("ssh", {})
    SSH_USER = ssh.get("user", "svcjira")
    SSH_TIMEOUT = ssh.get("timeout", 10)
    
    # Settings
    settings = instance_config.get("settings", {})
    ACCESS_LOG_FORMAT = settings.get("access_log_format", "access_log.%Y-%m-%d")
    REFRESH_INTERVAL = settings.get("refresh_interval", 5)
    
    # Thresholds
    thresholds = instance_config.get("thresholds", {})
    THRESHOLD_MS = thresholds.get("response_time_ms", 60000)
    TAIL_LINES = thresholds.get("tail_lines", 5000)
else:
    # Default values (fallback - replace with your server details)
    JIRA_SERVERS = [
        {
            "name": "Jira Server 1",
            "hostname": "jira-server-1.example.com",
            "log_path": "/export/jira/logs"
        },
    ]
    SSH_USER = "svcjira"
    SSH_TIMEOUT = 10
    ACCESS_LOG_FORMAT = "access_log.%Y-%m-%d"
    TAIL_LINES = 5000
    THRESHOLD_MS = 60000
    REFRESH_INTERVAL = 5

# --- Log Parsing Configuration ---
# Access log format assumptions:
# Field $3 = User ID
# Field $4 = Timestamp (with brackets)
# Field $10 = Time taken in milliseconds
# Adjust if your log format differs
