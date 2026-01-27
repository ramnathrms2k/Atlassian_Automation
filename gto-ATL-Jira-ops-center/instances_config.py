# instances_config.py
# Centralized configuration for all Jira instances/environments

INSTANCES = {
    "vmw-jira-prod": {
        "display_name": "VMW-Jira-Prod",
        "description": "VMware Jira Production Environment",
        
        # Jira Application Servers
        "jira_servers": [
            {
                "name": "Jira Server 1 (Prod A)",
                "hostname": "jira-server-1.example.com",
                "url": "http://jira-server-1.example.com:8080",
                "log_path": "/export/jira/logs"
            },
            {
                "name": "Jira Server 2 (Prod B)",
                "hostname": "jira-server-2.example.com",
                "url": "http://jira-server-2.example.com:8080",
                "log_path": "/export/jira/logs"
            },
            {
                "name": "Jira Server 3 (Prod C)",
                "hostname": "jira-server-3.example.com",
                "url": "http://jira-server-3.example.com:8080",
                "log_path": "/export/jira/logs"
            }
        ],
        
        # Database Server Configuration
        "db_server": {
            "name": "Database Server",
            "hostname": "db-server.example.com",
            "db_name": "jiradb",
            "db_user": "atlassian_readonly",
            "db_password": "TOKEN"  # Replace with actual password or use environment variable
        },
        
        # SSH Configuration
        "ssh": {
            "user": "svcjira",
            "timeout": 10  # seconds
        },
        
        # Paths Configuration
        "paths": {
            "jira_install": "/export/jira",
            "jira_home": "/export/jirahome",
            "log_path": "/export/jira/logs",
            "shared_home": "/projects/atlassian-jira/sharehome"
        },
        
        # Credentials (sensitive - use environment variables in production)
        "credentials": {
            "jira_pat": "TOKEN",  # Jira Personal Access Token - use environment variable JIRA_OPS_VMW_JIRA_PROD_JIRA_PAT
            "db_password": "TOKEN"  # Database password - use environment variable JIRA_OPS_VMW_JIRA_PROD_DB_PASSWORD
        },
        
        # Jira Configuration
        "jira": {
            "version": "10.3.12",
            "db_validation_user": "atlassian_readonly"
        },
        
        # Framework-Specific Thresholds
        "thresholds": {
            # Health Dashboard Thresholds
            "db_max_connections": 1500,
            "db_pool_per_app_node": 250,
            "db_connection_thresholds": {
                "green_max": 0.80,    # < 80% = Green
                "yellow_max": 0.90,  # 80-90% = Yellow
            },
            "system_thresholds": {
                "cpu": {
                    "green_max": 70,
                    "yellow_max": 85
                },
                "memory": {
                    "green_max": 75,
                    "yellow_max": 90
                },
                "swap": {
                    "green_max": 50,
                    "yellow_max": 80
                },
                "load": {
                    "green_max": 1.0,
                    "yellow_max": 2.0
                },
                "disk": {
                    "green_max": 75,
                    "yellow_max": 90
                }
            },
            # Response Time Tracker Thresholds
            "response_time_ms": 60000,  # 60 seconds
            "tail_lines": 5000,
            # Preflight Validator
            "jira_api_timeout": 60,
            "db_connect_timeout": 10,
            "db_read_timeout": 30
        },
        
        # Framework-Specific Settings
        "settings": {
            "access_log_format": "access_log.%Y-%m-%d",
            "auto_refresh_interval": 120,  # seconds
            "refresh_interval": 5,  # seconds (for response tracker)
            # Script Executor Settings
            "script_dir": "/export/scripts/",
            "script_name": "monitor_jira_v22.sh",
            "script_timeout": 20  # seconds
        }
    }
    
    # Add more instances here as needed:
    # "vmw-jira-staging": { ... },
    # "vmw-jira-dev": { ... },
}
