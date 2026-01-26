# config.py

# --- Jira Server Configuration ---
# Add your servers here. Each server should have hostname and log path.
JIRA_SERVERS = [
    {
        "name": "Jira Server 1",
        "hostname": "jira-server-1.example.com",
        "log_path": "/export/jira/logs"
    },
    {
        "name": "Jira Server 2",
        "hostname": "jira-server-2.example.com",
        "log_path": "/export/jira/logs"
    },
    {
        "name": "Jira Server 3",
        "hostname": "jira-server-3.example.com",
        "log_path": "/export/jira/logs"
    },
]

# --- SSH Configuration ---
SSH_USER = "your_ssh_user"  # Replace with your SSH username
SSH_TIMEOUT = 10  # seconds

# --- Access Log Configuration ---
ACCESS_LOG_FORMAT = "access_log.%Y-%m-%d"  # Format for today's log file (strftime format)
# Example: "access_log.2026-01-21" for format "access_log.%Y-%m-%d"

# --- Analysis Configuration ---
TAIL_LINES = 5000  # Number of lines to tail from the access log
THRESHOLD_MS = 60000  # Threshold in milliseconds (requests taking longer than this will be tracked)
REFRESH_INTERVAL = 5  # Refresh interval in seconds (for auto-refresh, if implemented)

# --- Log Parsing Configuration ---
# Access log format assumptions:
# Field $3 = User ID
# Field $4 = Timestamp (with brackets)
# Field $10 = Time taken in milliseconds
# Adjust if your log format differs
