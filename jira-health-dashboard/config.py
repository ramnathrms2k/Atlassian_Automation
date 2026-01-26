# config.py

# --- Jira Server Configuration ---
# Add your servers here. The "name" is for display, "url" is the base URL.
JIRA_SERVERS = [
    {"name": "Jira Server 1 (Prod A)", "url": "http://jira-lvnv-it-101.lvn.broadcom.net:8080"},
    {"name": "Jira Server 2 (Prod B)", "url": "http://jira-lvnv-it-102.lvn.broadcom.net:8080"},
    {"name": "Jira Server 3 (Prod C)", "url": "http://jira-lvnv-it-103.lvn.broadcom.net:8080"},
]

# --- Personal Access Token ---
# For better security, consider loading this from an environment variable
JIRA_PAT = "TOKEN"
