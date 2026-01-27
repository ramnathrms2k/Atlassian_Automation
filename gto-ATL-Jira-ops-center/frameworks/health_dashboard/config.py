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
    _injected_config = _get_injected('health-dashboard')
except:
    pass

# Use injected config if available, otherwise use defaults
if _injected_config:
    instance_config = _injected_config
    
    # Jira Server Configuration
    JIRA_SERVERS = [
        {
            "name": server["name"],
            "url": server["url"],
            "hostname": server["hostname"]
        }
        for server in instance_config.get("jira_servers", [])
    ]
    
    # Database Server Configuration
    db_server = instance_config.get("db_server", {})
    DB_SERVER = {
        "name": db_server.get("name", "Database Server"),
        "hostname": db_server.get("hostname", ""),
        "db_name": db_server.get("db_name", "jiradb"),
        "db_user": db_server.get("db_user", "atlassian_readonly"),
        "db_password": db_server.get("db_password", "TOKEN")
    }
    
    # Credentials
    credentials = instance_config.get("credentials", {})
    JIRA_PAT = credentials.get("jira_pat", "TOKEN")
    
    # SSH Configuration
    ssh = instance_config.get("ssh", {})
    SSH_USER = ssh.get("user", "svcjira")
    SSH_TIMEOUT = ssh.get("timeout", 10)
    
    # Thresholds
    thresholds = instance_config.get("thresholds", {})
    JIRA_API_TIMEOUT = thresholds.get("jira_api_timeout", 60)
    DB_CONNECT_TIMEOUT = thresholds.get("db_connect_timeout", 10)
    DB_READ_TIMEOUT = thresholds.get("db_read_timeout", 30)
    AUTO_REFRESH_INTERVAL = instance_config.get("settings", {}).get("auto_refresh_interval", 120)
    
    DB_MAX_CONNECTIONS = thresholds.get("db_max_connections", 1500)
    DB_POOL_PER_APP_NODE = thresholds.get("db_pool_per_app_node", 250)
    DB_CONNECTION_THRESHOLDS = thresholds.get("db_connection_thresholds", {
        "green_max": 0.80,
        "yellow_max": 0.90
    })
    SYSTEM_THRESHOLDS = thresholds.get("system_thresholds", {
        "cpu": {"green_max": 70, "yellow_max": 85},
        "memory": {"green_max": 75, "yellow_max": 90},
        "swap": {"green_max": 50, "yellow_max": 80},
        "load": {"green_max": 1.0, "yellow_max": 2.0},
        "disk": {"green_max": 75, "yellow_max": 90}
    })
else:
    # Default values (fallback)
    JIRA_SERVERS = []
    DB_SERVER = {}
    JIRA_PAT = "TOKEN"
    SSH_USER = "svcjira"
    SSH_TIMEOUT = 10
    JIRA_API_TIMEOUT = 60
    DB_CONNECT_TIMEOUT = 10
    DB_READ_TIMEOUT = 30
    AUTO_REFRESH_INTERVAL = 120
    DB_MAX_CONNECTIONS = 1500
    DB_POOL_PER_APP_NODE = 250
    DB_CONNECTION_THRESHOLDS = {"green_max": 0.80, "yellow_max": 0.90}
    SYSTEM_THRESHOLDS = {
        "cpu": {"green_max": 70, "yellow_max": 85},
        "memory": {"green_max": 75, "yellow_max": 90},
        "swap": {"green_max": 50, "yellow_max": 80},
        "load": {"green_max": 1.0, "yellow_max": 2.0},
        "disk": {"green_max": 75, "yellow_max": 90}
    }
