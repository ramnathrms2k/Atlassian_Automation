"""
On-demand analysis: fetch access logs via SSH, parse, filter, compute z-scores, produce CSV and chart data.
"""
import subprocess
import csv
import io
import shlex
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any

from load_config import get_config, get_ssh_user, get_ssh_timeout, get_ssh_options, get_product, get_log_file_for_date, get_log_pattern_type
from parser import parse_lines, add_z_scores, add_apdex_category, compute_apdex


def run_ssh(hostname: str, command: str, timeout: Optional[int] = None) -> Dict[str, Any]:
    """Run command on host via SSH. Returns {success, output, error}. timeout is connect timeout; run timeout is timeout+10 or 120 for long fetches."""
    user = get_ssh_user()
    to = timeout or get_ssh_timeout()
    opts = get_ssh_options()
    run_timeout = max(to + 10, 120) if timeout and timeout > 60 else (to + 10)
    ssh_cmd = ["ssh", "-o", f"ConnectTimeout={to}", *opts, f"{user}@{hostname}", command]
    try:
        result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=run_timeout)
        if result.returncode == 0:
            return {"success": True, "output": result.stdout or "", "error": None}
        return {"success": False, "output": None, "error": (result.stderr or result.stdout or "Unknown error").strip()}
    except subprocess.TimeoutExpired:
        return {"success": False, "output": None, "error": "SSH timeout"}
    except Exception as e:
        return {"success": False, "output": None, "error": str(e)}


def fetch_log_content(
    hostname: str,
    log_path: str,
    log_file_pattern: str,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    days: Optional[int] = None,
    uri_filter: Optional[str] = None,
    user_filter: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fetch log file content from remote host. Fetches day-by-day to avoid timeouts on large ranges.
    When uri_filter or user_filter is set, uses server-side grep -F to transfer only matching lines.
    """
    end = to_date or datetime.now()
    if from_date is not None and to_date is not None:
        start = min(from_date, to_date)
        end = max(from_date, to_date)
    elif days is not None and days >= 1:
        start = end - timedelta(days=days - 1)
    else:
        start = end
    # Build grep pattern for request line only (avoid matching Referer/User-Agent). Request looks like "METHOD /path?query HTTP/1.1"
    def _grep_pattern_uri(uf: str) -> str:
        uf = uf.strip()
        if not uf:
            return uf
        # Match " /uri" or "METHOD /uri" so we don't match Referer (https://...)
        if uf.startswith("/"):
            return " " + uf  # space + /path matches "GET /path" not "https://host/path"
        return uf

    # Single day
    if start == end and (from_date is None or to_date is None) and not (days and days > 1):
        path, fname = _log_file_for_date_in_product(log_path, log_file_pattern, end)
        if uri_filter and uri_filter.strip():
            cmd = f"grep -F {shlex.quote(_grep_pattern_uri(uri_filter))} {path}/{fname} 2>/dev/null || true"
        elif user_filter and user_filter.strip():
            cmd = f"grep -F {shlex.quote(user_filter.strip())} {path}/{fname} 2>/dev/null || true"
        else:
            cmd = f"cat {path}/{fname} 2>/dev/null || true"
        result = run_ssh(hostname, cmd, timeout=90 if not (uri_filter or user_filter) else None)
        if result["success"]:
            return {"success": True, "content": result["output"] or "", "error": None}
        return {"success": False, "content": None, "error": result["error"]}
    # Multiple days: fetch one file per SSH call to avoid timeout and use grep when filter set
    combined = []
    d = start
    fetch_timeout = 90
    while d <= end:
        path, fname = _log_file_for_date_in_product(log_path, log_file_pattern, d)
        full = f"{path}/{fname}"
        if uri_filter and uri_filter.strip():
            cmd = f"grep -F {shlex.quote(_grep_pattern_uri(uri_filter))} {full} 2>/dev/null || true"
        elif user_filter and user_filter.strip():
            cmd = f"grep -F {shlex.quote(user_filter.strip())} {full} 2>/dev/null || true"
        else:
            cmd = f"cat {full} 2>/dev/null || true"
        result = run_ssh(hostname, cmd, timeout=fetch_timeout)
        if not result["success"]:
            return {"success": False, "content": None, "error": result["error"]}
        if result.get("output"):
            combined.append(result["output"])
        d += timedelta(days=1)
    content = "\n".join(combined) if combined else ""
    return {"success": True, "content": content, "error": None}


def _log_file_for_date_in_product(log_path: str, log_file_pattern: str, d: datetime) -> tuple:
    """Resolve log path and filename for date (strftime on pattern)."""
    try:
        fname = d.strftime(log_file_pattern)
    except (ValueError, TypeError):
        fname = log_file_pattern.replace("%Y", str(d.year)).replace("%m", f"{d.month:02d}").replace("%d", f"{d.day:02d}")
    return log_path, fname


def _percentile_sorted(sorted_values: List[float], p: float) -> float:
    """p in 0..100. sorted_values must be sorted ascending."""
    if not sorted_values:
        return 0
    k = (len(sorted_values) - 1) * (p / 100.0)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def compute_summary_stats(records: List[Dict]) -> Dict[str, Any]:
    """Compute access_log (users, requests, uris, p99, p95, p90, avg) and apdex (score, satisfied, neutral, not_satisfied)."""
    if not records:
        return {
            "access_log": {"users": 0, "requests": 0, "uris": 0, "p99_ms": 0, "p95_ms": 0, "p90_ms": 0, "avg_ms": 0},
            "apdex": {"score": 0, "satisfied": 0, "neutral": 0, "not_satisfied": 0},
        }
    users = len(set(r.get("user") or "" for r in records))
    requests = len(records)
    uris = len(set(r.get("uri") or "" for r in records))
    times = sorted([r.get("response_time_ms") or 0 for r in records])
    p99 = _percentile_sorted(times, 99)
    p95 = _percentile_sorted(times, 95)
    p90 = _percentile_sorted(times, 90)
    avg = sum(times) / len(times) if times else 0
    score, sat, neu, not_sat = compute_apdex(records)
    return {
        "access_log": {"users": users, "requests": requests, "uris": uris, "p99_ms": round(p99, 2), "p95_ms": round(p95, 2), "p90_ms": round(p90, 2), "avg_ms": round(avg, 2)},
        "apdex": {"score": score, "satisfied": sat, "neutral": neu, "not_satisfied": not_sat},
    }


def filter_records(records: List[Dict], user_filter: Optional[str] = None, uri_filter: Optional[str] = None) -> List[Dict]:
    """Filter by user and URI using literal substring (contains); no regex, so special chars are matched as-is."""
    out = records
    if user_filter and user_filter.strip():
        u = user_filter.strip().lower()
        out = [r for r in out if (r.get("user") or "").lower().find(u) >= 0]
    if uri_filter and uri_filter.strip():
        ur = uri_filter.strip().lower()
        # Filter against full URI (path + query) so e.g. /Dashboard.jspa?selectPageId=98308 works
        out = [r for r in out if (r.get("uri_full") or r.get("uri") or "").lower().find(ur) >= 0]
    return out


def run_on_demand_analysis(
    product_id: str,
    node_names: Optional[List[str]] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    days: Optional[int] = 1,
    user_filter: Optional[str] = None,
    uri_filter: Optional[str] = None,
    cumulative: bool = True,
) -> Dict[str, Any]:
    """
    Run analysis: fetch logs from selected nodes (or all), parse, filter, add z-scores.
    If cumulative=True, merge all nodes and sort by time, add node column. Else return per-node data.
    Returns { success, per_node: { node_name: [records] }, cumulative: [records], csv_string, error }.
    """
    product = get_product(product_id)
    if not product:
        return {"success": False, "error": f"Unknown product: {product_id}", "per_node": {}, "cumulative": [], "csv_string": ""}
    nodes = product.get("nodes", [])
    if node_names:
        nodes = [n for n in nodes if n["name"] in node_names]
    if not nodes:
        return {"success": False, "error": "No nodes selected", "per_node": {}, "cumulative": [], "csv_string": ""}
    pattern_type = product.get("log_pattern_type") or get_log_pattern_type()
    to_dt = to_date or datetime.now()
    if from_date is not None and to_date is not None:
        from_dt, to_dt = min(from_date, to_date), max(from_date, to_date)
    else:
        from_dt = from_date or ((to_dt - timedelta(days=days - 1)) if days else to_dt)
    per_node = {}
    all_records = []
    for node in nodes:
        log_path = node["log_path"]
        log_file_pattern = node["log_file_pattern"]
        hostname = node["hostname"]
        name = node["name"]
        fetch = fetch_log_content(
            hostname, log_path, log_file_pattern,
            from_date=from_dt, to_date=to_dt,
            days=days if from_date is None or to_date is None else None,
            uri_filter=uri_filter,
            user_filter=user_filter,
        )
        if not fetch["success"]:
            per_node[name] = {"error": fetch["error"], "records": []}
            continue
        raw = fetch["content"]
        lines = [ln for ln in raw.splitlines() if ln.strip()]
        records = parse_lines(lines, pattern_type, node_name=name)
        records = filter_records(records, user_filter=user_filter, uri_filter=uri_filter)
        add_z_scores(records)
        add_apdex_category(records)
        per_node[name] = {"records": records, "error": None}
        all_records.extend(records)
    # Cumulative: sort by timestamp, add node column (already in each record)
    all_records.sort(key=lambda r: (r.get("timestamp") or "", r.get("node") or ""))
    add_z_scores(all_records)  # recompute z over combined set
    add_apdex_category(all_records)
    summary = compute_summary_stats(all_records)
    per_node_summary = {}
    for node_name, recs in per_node.items():
        rec_list = recs.get("records") if isinstance(recs, dict) else recs
        if rec_list:
            per_node_summary[node_name] = compute_summary_stats(rec_list)
    # Build CSV: full URI in display, column header "Anomaly Score" for z_score
    columns = ["timestamp", "node", "user", "uri", "response_time_ms", "anomaly_score", "apdex_category"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=columns, extrasaction="ignore")
    w.writeheader()
    def _csv_row(rec):
        return {
            "timestamp": rec.get("timestamp"),
            "node": rec.get("node"),
            "user": rec.get("user"),
            "uri": rec.get("uri_full") or rec.get("uri"),
            "response_time_ms": rec.get("response_time_ms"),
            "anomaly_score": rec.get("z_score"),
            "apdex_category": rec.get("apdex_category"),
        }
    for r in (all_records if cumulative else []):
        w.writerow(_csv_row(r))
    if not cumulative:
        for _node_name, data in per_node.items():
            for r in data.get("records") or []:
                w.writerow(_csv_row(r))
    csv_string = buf.getvalue()
    return {
        "success": True,
        "per_node": {k: v.get("records", []) for k, v in per_node.items()},
        "cumulative": all_records,
        "csv_string": csv_string,
        "summary": summary,
        "per_node_summary": per_node_summary,
        "error": None,
    }


def records_to_csv_rows(records: List[Dict], include_node: bool = True) -> List[Dict]:
    """For JSON/table: list of dicts with keys timestamp, [node], user, uri, response_time_ms, z_score."""
    cols = ["timestamp", "user", "uri", "response_time_ms", "z_score"]
    if include_node:
        cols = ["timestamp", "node", "user", "uri", "response_time_ms", "z_score"]
    return [{k: r.get(k) for k in cols if k in r} for r in records]
