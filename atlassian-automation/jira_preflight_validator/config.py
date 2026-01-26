import os

# --- CONNECTIVITY ---
SSH_USER = "svcjira"
HOSTS = [
    "jira-lvnv-it-101.lvn.broadcom.net",
    "jira-lvnv-it-102.lvn.broadcom.net",
    "jira-lvnv-it-103.lvn.broadcom.net"
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
DB_PASSWORD = "TOKEN"
