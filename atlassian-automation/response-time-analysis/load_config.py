"""
Load configuration from config/config.yaml.
All paths and product/node definitions are variabilized.
"""
import os
from datetime import datetime

try:
    import yaml
except ImportError:
    yaml = None

# Default config path relative to project root
CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.yaml")

_cached_config = None


def get_config(path=None):
    """Load and return config dict. Uses cache after first load."""
    global _cached_config
    if _cached_config is not None and path is None:
        return _cached_config
    if yaml is None:
        raise RuntimeError("PyYAML is required. Install with: pip install pyyaml")
    config_path = path or CONFIG_PATH
    with open(config_path, "r") as f:
        _cached_config = yaml.safe_load(f)
    return _cached_config


def get_ssh_user():
    return get_config().get("ssh_user", "svcjira")


def get_ssh_timeout():
    return get_config().get("ssh_timeout_seconds", 15)


def get_ssh_options():
    return get_config().get("ssh_options", ["-o", "StrictHostKeyChecking=no"])


def get_products():
    """Return dict of product_id -> { display_name, nodes, ... }."""
    return get_config().get("products", {})


def get_product(product_id):
    """Return single product config or None."""
    return get_products().get(product_id)


def get_log_file_for_date(product_id, node, d):
    """Get log file name for a given product node and date.
    node has log_path and log_file_pattern (strftime).
    """
    prod = get_product(product_id)
    if not prod:
        return None, None
    log_path = node.get("log_path", "")
    pattern = node.get("log_file_pattern", "access_log.%Y-%m-%d")
    try:
        filename = d.strftime(pattern)
    except (ValueError, TypeError):
        filename = pattern.replace("%Y", str(d.year)).replace("%m", f"{d.month:02d}").replace("%d", f"{d.day:02d}")
    return log_path, filename


def get_flask_port():
    return get_config().get("flask_port", 9090)


def get_default_days():
    return get_config().get("default_days", 1)


def get_default_z_threshold():
    return get_config().get("default_z_threshold", 2.0)


def get_log_pattern_type():
    return get_config().get("log_pattern_type", "common_with_D")
