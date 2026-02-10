"""
Parse Tomcat AccessLogValve access logs.
Supports common_with_D: %h %l %u %t "%r" %s %b %D
and combined_with_D (extra Referer/User-Agent before %D).
Extracts: timestamp, user, uri (path without query), response_time_ms.
"""
import re
from datetime import datetime

# Common/combined with %D: IP ident user [date] "METHOD /path?query HTTP/x.x" status bytes [optional "ref" "ua"] time_ms
# Capture full request URI (path + query) for filtering; we derive path-only for display.
_RE_COMMON = re.compile(
    r'^\S+\s+\S+\s+(\S+)\s+\[([^\]]+)\]\s+"(?:GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\s+(\S+)\s+[^"]+"\s+(.+)$'
)

# Confluence: [date] user thread IP METHOD /path?query HTTP/1.1 status 285ms bytes ...
_RE_CONFLUENCE = re.compile(
    r'^\[([^\]]+)\]\s+(\S+)\s+\S+\s+\S+\s+(?:GET|POST|PUT|DELETE|HEAD|OPTIONS|PATCH)\s+(\S+)\s+HTTP/1\.\d\s+\d+\s+(\d+)ms\s'
)


def _parse_timestamp(ts_str):
    """Parse CLF timestamp [10/Feb/2026:12:00:00 +0000] to ISO-like string for consistency."""
    ts_str = ts_str.strip()
    try:
        # 10/Feb/2026:12:00:00 +0000
        dt = datetime.strptime(ts_str[:20], "%d/%b/%Y:%H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, IndexError):
        return ts_str


def _response_time_from_trailing(trailing):
    """From trailing part after the request quote, get last numeric token (response time in ms)."""
    parts = trailing.split()
    for i in range(len(parts) - 1, -1, -1):
        s = parts[i].strip()
        if s.isdigit():
            return int(s)
        if s.replace(".", "", 1).isdigit():
            return int(float(s))
    return None


def parse_line(line, pattern_type="common_with_D"):
    """
    Parse a single access log line.
    Returns dict with keys: timestamp, user, uri, uri_full, response_time_ms, or None if unparseable.
    pattern_type: common_with_D (Tomcat/Jira) or confluence (Confluence native format).
    """
    if not line or not line.strip():
        return None
    line = line.strip()
    if pattern_type == "confluence":
        m = _RE_CONFLUENCE.match(line)
        if not m:
            return None
        ts_str, user, uri_full, response_ms = m.group(1), m.group(2), m.group(3), int(m.group(4))
        uri_path = uri_full.split("?")[0] if "?" in uri_full else uri_full
        return {
            "timestamp": _parse_timestamp(ts_str),
            "user": user,
            "uri": uri_path,
            "uri_full": uri_full,
            "response_time_ms": response_ms,
        }
    m = _RE_COMMON.match(line)
    if not m:
        return None
    user, ts_str, uri_full, trailing = m.groups()
    response_ms = _response_time_from_trailing(trailing)
    if response_ms is None:
        return None
    uri_path = uri_full.split("?")[0] if "?" in uri_full else uri_full
    return {
        "timestamp": _parse_timestamp(ts_str),
        "user": user,
        "uri": uri_path,
        "uri_full": uri_full,
        "response_time_ms": response_ms,
    }


def parse_lines(lines, pattern_type="common_with_D", node_name=None):
    """Parse multiple lines; add node_name to each record if provided."""
    rows = []
    for line in lines:
        if not line.strip():
            continue
        rec = parse_line(line, pattern_type)
        if rec:
            if node_name:
                rec["node"] = node_name
            rows.append(rec)
    return rows


def compute_z_scores(values):
    """Compute z-scores for a list of numbers. Returns list of (value, z_score)."""
    import statistics
    if not values or len(values) < 2:
        return [(v, 0.0) for v in values]
    mean = statistics.mean(values)
    stdev = statistics.stdev(values)
    if stdev == 0:
        return [(v, 0.0) for v in values]
    return [(v, (v - mean) / stdev) for v in values]


def add_z_scores(records, key="response_time_ms"):
    """Add z_score to each record based on key field. Modifies records in place; returns records."""
    values = [r[key] for r in records]
    z_list = compute_z_scores(values)
    for r, (_, z) in zip(records, z_list):
        r["z_score"] = round(z, 4)
    return records


# APDEX: < 2s satisfied, 2-5s neutral, > 5s not_satisfied. Score = (satisfied + 0.5*neutral) / total
APDEX_SATISFIED_MS = 2000
APDEX_NEUTRAL_MS = 5000


def add_apdex_category(records, key="response_time_ms"):
    """Set apdex_category on each record: satisfied | neutral | not_satisfied. Modifies in place."""
    for r in records:
        ms = r.get(key) or 0
        if ms < APDEX_SATISFIED_MS:
            r["apdex_category"] = "satisfied"
        elif ms <= APDEX_NEUTRAL_MS:
            r["apdex_category"] = "neutral"
        else:
            r["apdex_category"] = "not_satisfied"
    return records


def compute_apdex(records, key="response_time_ms"):
    """Return (score, satisfied_count, neutral_count, not_satisfied_count)."""
    satisfied = sum(1 for r in records if (r.get(key) or 0) < APDEX_SATISFIED_MS)
    neutral = sum(1 for r in records if APDEX_SATISFIED_MS <= (r.get(key) or 0) <= APDEX_NEUTRAL_MS)
    not_satisfied = sum(1 for r in records if (r.get(key) or 0) > APDEX_NEUTRAL_MS)
    total = len(records)
    score = (satisfied + 0.5 * neutral) / total if total else 0
    return round(score, 4), satisfied, neutral, not_satisfied
