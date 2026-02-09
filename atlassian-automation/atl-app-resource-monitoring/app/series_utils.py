"""
Z-score, trend, and extended row building for time-series CSV.
Matches frontend logic so backend can produce the same extended rows when collecting in background.
"""
from typing import Any


def _parse_ts_ms(ts: Any) -> float:
    """Parse timestamp (str or number) to milliseconds since epoch."""
    if ts is None:
        return 0.0
    if isinstance(ts, (int, float)):
        return float(ts) if ts > 1e12 else ts * 1000  # assume sec if small
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
        return dt.timestamp() * 1000
    except Exception:
        return 0.0


def compute_z_score_map(
    series: list[dict],
    current_row: dict,
    window_ms: int,
) -> dict[str, float]:
    """
    Compute Z-score for each numeric column from rows in the time window.
    series: list of row dicts (each has 'timestamp' and metric keys).
    current_row: the new row (with timestamp).
    """
    result = {}
    if not series:
        return result
    try:
        current_ts = _parse_ts_ms(current_row.get("timestamp"))
        cutoff = current_ts - window_ms
    except Exception:
        cutoff = 0
    keys = [k for k in series[0].keys() if k != "timestamp" and not k.endswith("_z") and not k.endswith("_z_color") and not k.endswith("_trend") and not k.endswith("_pred")]
    for key in keys:
        values = []
        for row in series:
            ts = _parse_ts_ms(row.get("timestamp"))
            if ts < cutoff:
                continue
            v = row.get(key)
            if v is None or v == "":
                continue
            try:
                n = float(v)
                if n != n:
                    continue
                values.append(n)
            except (TypeError, ValueError):
                continue
        cur = current_row.get(key)
        if cur is None or cur == "":
            continue
        try:
            cur_n = float(cur)
            if cur_n != cur_n:
                continue
        except (TypeError, ValueError):
            continue
        if len(values) < 2:
            result[key] = 0.0
            continue
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std = variance ** 0.5
        if std == 0:
            result[key] = 0.0
            continue
        result[key] = (cur_n - mean) / std
    return result


def compute_trend_map(prev_row: dict | None, current_row: dict | None) -> dict[str, int]:
    """Trend: 1 = up, -1 = down, 0 = stable (per key)."""
    result = {}
    if not prev_row or not current_row:
        return result
    keys = [k for k in current_row if k != "timestamp"]
    for key in keys:
        cur = current_row.get(key)
        prev = prev_row.get(key)
        if cur is None or cur == "" or prev is None or prev == "":
            continue
        try:
            cn, pn = float(cur), float(prev)
            if cn != cn or pn != pn:
                continue
            if cn > pn:
                result[key] = 1
            elif cn < pn:
                result[key] = -1
            else:
                result[key] = 0
        except (TypeError, ValueError):
            continue
    return result


def get_z_score_color_label(z_score: float | None, config: dict) -> str:
    """Return green | yellow | red from z_score thresholds."""
    if z_score is None or (isinstance(z_score, float) and z_score != z_score):
        return "green"
    n = config.get("normal_max", 1.75)
    m = config.get("medium_max", 2.75)
    abs_z = abs(z_score)
    if abs_z <= n:
        return "green"
    if abs_z <= m:
        return "yellow"
    return "red"


def _higher_is_better(key: str) -> bool:
    return "mem_avail_pct" in key or "heap_avail_pct" in key or key == "apdex" or (key or "").startswith("apdex")


def get_prediction_label(trend_dir: int, column_key: str) -> str:
    if trend_dir == 0:
        return "neutral"
    higher_better = _higher_is_better(column_key)
    if trend_dir > 0:
        return "improve" if higher_better else "worsen"
    return "worsen" if higher_better else "improve"


def build_extended_columns(base_columns: list[str]) -> list[str]:
    """Extended columns: for each base col (except timestamp) add _z, _z_color, _trend, _pred."""
    out = []
    for c in base_columns:
        out.append(c)
        if c != "timestamp":
            out.extend([c + "_z", c + "_z_color", c + "_trend", c + "_pred"])
    return out


def build_extended_row(
    base_row: dict,
    z_score_map: dict[str, float],
    trend_map: dict[str, int],
    base_columns: list[str],
    z_config: dict,
) -> dict[str, Any]:
    """Build one extended row with _z, _z_color, _trend, _pred per base column."""
    ext = dict(base_row)
    for col in base_columns:
        if col == "timestamp":
            continue
        z = z_score_map.get(col)
        ext[col + "_z"] = round(z, 3) if z is not None and z == z else ""
        ext[col + "_z_color"] = get_z_score_color_label(z, z_config) if z is not None else "green"
        t = trend_map.get(col)
        ext[col + "_trend"] = "up" if t == 1 else ("down" if t == -1 else "")
        ext[col + "_pred"] = get_prediction_label(t or 0, col)
    return ext
