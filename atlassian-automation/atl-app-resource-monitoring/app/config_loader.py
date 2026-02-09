"""
Load and merge default config with environment-specific config.
Server list, paths, and env details are isolated for reuse in other environments.
"""
import os
from pathlib import Path

import yaml

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
DEFAULT_CONFIG = CONFIG_DIR / "default.yaml"
ENVIRONMENTS_DIR = CONFIG_DIR / "environments"


def list_environments() -> list[str]:
    """Return available environment names (from .yaml filenames in config/environments/)."""
    if not ENVIRONMENTS_DIR.exists():
        return []
    names = []
    for f in sorted(ENVIRONMENTS_DIR.iterdir()):
        if f.suffix.lower() == ".yaml" and f.name.startswith(".") is False:
            names.append(f.stem)
    return names


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def _deep_merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if k in out and isinstance(out[k], dict) and isinstance(v, dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out


def get_config(environment: str = None) -> dict:
    """Load default config and overlay environment config. environment e.g. 'VMW-Jira'."""
    base = _load_yaml(DEFAULT_CONFIG)
    available = list_environments()
    env_name = environment or os.environ.get("JIRA_MONITOR_ENV") or (available[0] if available else None)
    if not env_name or (available and env_name not in available):
        env_name = available[0] if available else "default"
    env_path = ENVIRONMENTS_DIR / f"{env_name}.yaml"
    env_cfg = _load_yaml(env_path)
    return _deep_merge(base, env_cfg)


def get_servers_full_hostnames(config: dict) -> list[str]:
    """Return list of FQDN hostnames for SSH."""
    servers = config.get("servers", [])
    domain = config.get("domain", "")
    if not domain.startswith("."):
        domain = "." + domain
    return [f"{s}{domain}" for s in servers]
