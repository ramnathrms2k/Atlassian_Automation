# config.py

# --- Jira Server Configuration ---
# Add your servers here. The "name" is for display, "url" is the base URL.
JIRA_SERVERS = [
    {"name": "Jira Server 1", "url": "http://jira-server-1.example.com:8080", "hostname": "jira-server-1.example.com"},
    {"name": "Jira Server 2", "url": "http://jira-server-2.example.com:8080", "hostname": "jira-server-2.example.com"},
    {"name": "Jira Server 3", "url": "http://jira-server-3.example.com:8080", "hostname": "jira-server-3.example.com"},
]

# --- Database Server Configuration ---
DB_SERVER = {
    "name": "Database Server",
    "hostname": "db-server.example.com",
    "db_name": "jiradb",
    "db_user": "atlassian_readonly",
    "db_password": "TOKEN"  # Replace TOKEN with actual database password
}

# --- Personal Access Token ---
# For better security, consider loading this from an environment variable
JIRA_PAT = "TOKEN"  # Replace TOKEN with actual Jira Personal Access Token

# --- SSH Configuration ---
SSH_USER = "your_ssh_user"  # Replace with your SSH username
SSH_TIMEOUT = 10  # seconds

# --- Jira API Configuration ---
JIRA_API_TIMEOUT = 60  # seconds (timeout for Jira API calls, index summary can take time)

# --- Database Connection Configuration ---
DB_CONNECT_TIMEOUT = 10  # seconds (MySQL connection timeout)
DB_READ_TIMEOUT = 30  # seconds (MySQL read timeout)

# --- Auto-Refresh Configuration ---
AUTO_REFRESH_INTERVAL = 120  # seconds (2 minutes - allows health checks to complete without overlap)

# --- Database Connection Thresholds ---
DB_MAX_CONNECTIONS = 1500
DB_POOL_PER_APP_NODE = 250
DB_CONNECTION_THRESHOLDS = {
    "green_max": 0.80,    # < 80% = Green (< 200 per app, < 1200 total)
    "yellow_max": 0.90,  # 80-90% = Yellow (200-225 per app, 1200-1350 total)
    # > 90% = Red (> 225 per app, > 1350 total)
}

# --- System Metrics Thresholds ---
SYSTEM_THRESHOLDS = {
    "cpu": {
        "green_max": 70,   # < 70% = Green
        "yellow_max": 85, # 70-85% = Yellow
        # > 85% = Red
    },
    "memory": {
        "green_max": 75,   # < 75% = Green
        "yellow_max": 90, # 75-90% = Yellow
        # > 90% = Red
    },
    "swap": {
        "green_max": 50,   # < 50% = Green
        "yellow_max": 80, # 50-80% = Yellow
        # > 80% = Red
    },
    "load": {
        "green_max": 1.0,  # < 1.0 = Green (per CPU core)
        "yellow_max": 2.0, # 1.0-2.0 = Yellow
        # > 2.0 = Red
    },
    "disk": {
        "green_max": 75,   # < 75% = Green
        "yellow_max": 90, # 75-90% = Yellow
        # > 90% = Red
    }
}
