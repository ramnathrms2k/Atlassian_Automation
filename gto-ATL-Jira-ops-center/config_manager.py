# config_manager.py
# Configuration injection and management

import os
from instances_config import INSTANCES

# Global storage for injected configuration
_injected_configs = {}

def get_instance_config(instance_id):
    """
    Get configuration for a specific instance.
    
    Args:
        instance_id: The instance identifier (e.g., 'vmw-jira-prod')
    
    Returns:
        dict: Instance configuration, or None if not found
    """
    if instance_id not in INSTANCES:
        return None
    
    config = INSTANCES[instance_id].copy()
    
    # Load credentials from environment variables if available
    # Format: JIRA_OPS_<INSTANCE_ID>_<CREDENTIAL_NAME>
    instance_upper = instance_id.upper().replace('-', '_')
    
    # Load Jira PAT
    pat_env = f"JIRA_OPS_{instance_upper}_JIRA_PAT"
    if pat_env in os.environ:
        config["credentials"]["jira_pat"] = os.environ[pat_env]
    
    # Load DB password
    db_pwd_env = f"JIRA_OPS_{instance_upper}_DB_PASSWORD"
    if db_pwd_env in os.environ:
        config["credentials"]["db_password"] = os.environ[db_pwd_env]
        config["db_server"]["db_password"] = os.environ[db_pwd_env]
    
    return config

def inject_config_to_framework(framework_id, instance_id):
    """
    Inject instance configuration into a framework's config module.
    
    Args:
        framework_id: The framework identifier
        instance_id: The instance identifier
    
    Returns:
        dict: The injected configuration
    """
    instance_config = get_instance_config(instance_id)
    if not instance_config:
        raise ValueError(f"Instance '{instance_id}' not found")
    
    # Store for framework access
    _injected_configs[framework_id] = instance_config
    
    return instance_config

def get_injected_config(framework_id):
    """
    Get the injected configuration for a framework.
    
    Args:
        framework_id: The framework identifier
    
    Returns:
        dict: The injected configuration, or None
    """
    return _injected_configs.get(framework_id)

def list_instances():
    """
    List all available instances.
    
    Returns:
        list: List of instance dictionaries with id and display_name
    """
    return [
        {
            "id": instance_id,
            "display_name": config.get("display_name", instance_id),
            "description": config.get("description", "")
        }
        for instance_id, config in INSTANCES.items()
    ]

def validate_instance_config(instance_id):
    """
    Validate that an instance configuration is complete.
    
    Args:
        instance_id: The instance identifier
    
    Returns:
        tuple: (is_valid, errors)
    """
    if instance_id not in INSTANCES:
        return False, [f"Instance '{instance_id}' not found"]
    
    config = INSTANCES[instance_id]
    errors = []
    
    # Required fields
    required_fields = [
        ("jira_servers", list),
        ("ssh", dict),
        ("paths", dict)
    ]
    
    for field, field_type in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")
        elif not isinstance(config[field], field_type):
            errors.append(f"Field '{field}' must be of type {field_type.__name__}")
    
    # Validate jira_servers structure
    if "jira_servers" in config:
        for i, server in enumerate(config["jira_servers"]):
            if "hostname" not in server:
                errors.append(f"jira_servers[{i}] missing 'hostname'")
            if "name" not in server:
                errors.append(f"jira_servers[{i}] missing 'name'")
    
    return len(errors) == 0, errors
