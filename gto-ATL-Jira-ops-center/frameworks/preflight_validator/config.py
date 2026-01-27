import os

# --- CONNECTIVITY ---
SSH_USER = "svcjira"
HOSTS = [
    "jira-server-1.example.com",
    "jira-server-2.example.com",
    "jira-server-3.example.com"
]

# --- JIRA CONFIGURATION ---
# These are injected into the script at runtime
JIRA_VERSION = "10.3.12"
JIRA_INSTALL_DIR = "/export/jira"
DB_VALIDATION_USER = "atlassian_readonly"

# --- LOCAL SETTINGS (JUMP SERVER) ---
# The folder where reports will be stored on this Jump Server
REPORT_DIR = os.path.join(os.getcwd(), "reports")
VALIDATOR_SCRIPT = "jira_node_validator_v10.py"

# --- SECRETS ---
# In production, load this from os.environ or a vault
# This will be overridden by instance configuration from instances_config.py
DB_PASSWORD = os.environ.get('ATLASSIAN_DB_PASSWORD', 'TOKEN')
