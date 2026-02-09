"""
Background collection: collect metrics for configured environments on an interval,
append extended rows to CSV (with migration if new columns), and write latest snapshot for UI.
"""
import csv
import json
import logging
from pathlib import Path
from typing import Any

from app.collector import collect_all
from app.config_loader import get_config, list_environments
from app.flatten import flatten_snapshot
from app.series_utils import (
    build_extended_columns,
    build_extended_row,
    compute_trend_map,
    compute_z_score_map,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _csv_path(environment: str) -> Path:
    cfg = get_config(environment)
    csv_dir = cfg.get("monitoring", {}).get("csv_directory", "data")
    p = PROJECT_ROOT / csv_dir
    p.mkdir(parents=True, exist_ok=True)
    return p / f"monitoring_{environment}.csv"


def _latest_path(environment: str) -> Path:
    cfg = get_config(environment)
    csv_dir = cfg.get("monitoring", {}).get("csv_directory", "data")
    p = PROJECT_ROOT / csv_dir
    p.mkdir(parents=True, exist_ok=True)
    return p / f"latest_{environment}.json"


def _base_columns(columns: list[str]) -> list[str]:
    return [
        c
        for c in columns
        if c == "timestamp"
        or not (
            c.endswith("_z")
            or c.endswith("_z_color")
            or c.endswith("_trend")
            or c.endswith("_pred")
        )
    ]


def _read_csv_rows(path: Path) -> tuple[list[str], list[dict]]:
    """Return (fieldnames, list of row dicts)."""
    if not path.exists():
        return [], []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def _ensure_csv_header_and_append(
    path: Path,
    extended_columns: list[str],
    extended_row: dict,
) -> None:
    """
    If file exists and has fewer columns than extended_columns, migrate (rewrite with new header).
    Then append the new row.
    """
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(extended_columns)
            w.writerow([extended_row.get(c, "") for c in extended_columns])
        return
    existing_header, existing_rows = _read_csv_rows(path)
    new_cols = [c for c in extended_columns if c not in existing_header]
    if not new_cols:
        with open(path, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([extended_row.get(c, "") for c in existing_header])
        return
    # Migrate: new header = existing_header + new_cols (keep order: all extended_columns)
    full_header = list(extended_columns)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(full_header)
        for row in existing_rows:
            w.writerow([row.get(c, "") for c in full_header])
        w.writerow([extended_row.get(c, "") for c in full_header])


def collect_and_append(environment: str) -> None:
    """Collect metrics for one environment, compute Z/trend, append to CSV, write latest JSON."""
    try:
        cfg = get_config(environment)
        data = collect_all(cfg)
    except Exception as e:
        logger.exception("Collect failed for %s: %s", environment, e)
        return
    try:
        base_columns, base_row = flatten_snapshot(data)
    except Exception as e:
        logger.exception("Flatten failed for %s: %s", environment, e)
        return
    path = _csv_path(environment)
    window_min = cfg.get("monitoring", {}).get("csv_window_minutes", 60)
    window_ms = int(window_min * 60 * 1000)
    z_config = (cfg.get("monitoring") or {}).get("z_score") or {}
    existing_header, existing_rows = _read_csv_rows(path)
    base_rows_for_z = []
    for r in existing_rows:
        base_rows_for_z.append({k: r.get(k) for k in base_columns if k in r or k in existing_header})
    base_rows_for_z = [r for r in base_rows_for_z if r.get("timestamp")]
    z_map = compute_z_score_map(base_rows_for_z, base_row, window_ms)
    prev_row = base_rows_for_z[-1] if base_rows_for_z else None
    trend_map = compute_trend_map(prev_row, base_row)
    extended_columns = build_extended_columns(base_columns)
    extended_row = build_extended_row(base_row, z_map, trend_map, base_columns, z_config)
    _ensure_csv_header_and_append(path, extended_columns, extended_row)
    latest_p = _latest_path(environment)
    try:
        with open(latest_p, "w", encoding="utf-8") as f:
            json.dump(data, f, default=str)
    except Exception as e:
        logger.warning("Write latest JSON failed for %s: %s", environment, e)


def run_background_tick(environments: list[str]) -> None:
    """Run one tick: collect and append for each environment."""
    for env in environments:
        try:
            collect_and_append(env)
        except Exception as e:
            logger.exception("Background tick failed for %s: %s", env, e)


def start_scheduler(interval_seconds: int, environments: list[str]) -> None:
    """Run background collection in a loop (blocking). Call from a daemon thread."""
    import time
    while True:
        if environments:
            run_background_tick(environments)
        time.sleep(interval_seconds)
