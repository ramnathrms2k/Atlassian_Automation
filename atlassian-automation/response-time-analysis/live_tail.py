"""
Live tail mode: SSH tail -F on selected nodes, parse lines, apply filters, push to queue for SSE.
"""
import uuid
import threading
import subprocess
import queue
from typing import Optional, List, Dict, Any
from datetime import datetime

from load_config import get_ssh_user, get_ssh_timeout, get_ssh_options, get_product, get_log_pattern_type
from parser import parse_line, add_z_scores, add_apdex_category

# session_id -> { "records": list, "queue": Queue, "stop": Event, "threads": list, "product_id", "node_names" }
_live_sessions: Dict[str, Dict[str, Any]] = {}
_sessions_lock = threading.Lock()


def _ssh_tail_reader(hostname: str, log_path: str, log_file: str, session_id: str, user_filter: Optional[str], uri_filter: Optional[str], pattern_type: str, node_name: str):
    """Run ssh tail -F and push parsed records to session queue. Runs until stop event."""
    session = _live_sessions.get(session_id)
    if not session:
        return
    q = session["queue"]
    stop = session["stop"]
    user = get_ssh_user()
    to = get_ssh_timeout()
    opts = get_ssh_options()
    cmd = ["ssh", "-o", f"ConnectTimeout={to}", *opts, f"{user}@{hostname}", f"tail -F {log_path}/{log_file} 2>/dev/null"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True, bufsize=1)
        while not stop.is_set():
            line = proc.stdout.readline()
            if not line:
                break
            rec = parse_line(line.strip(), pattern_type)
            if not rec:
                continue
            if user_filter and user_filter.strip() and (rec.get("user") or "").lower().find(user_filter.strip().lower()) < 0:
                continue
            if uri_filter and uri_filter.strip() and (rec.get("uri_full") or rec.get("uri") or "").lower().find(uri_filter.strip().lower()) < 0:
                continue
            rec["node"] = node_name
            with _sessions_lock:
                if session_id in _live_sessions:
                    _live_sessions[session_id]["records"].append(rec)
            q.put(rec)
        try:
            proc.terminate()
        except Exception:
            pass
    except Exception as e:
        q.put({"error": str(e), "node": node_name})
    finally:
        q.put(None)  # sentinel for this stream


def start_live_session(product_id: str, node_names: List[str], user_filter: Optional[str] = None, uri_filter: Optional[str] = None) -> Dict[str, Any]:
    """Start tail -F on given nodes. Returns session_id and current log file used."""
    product = get_product(product_id)
    if not product:
        return {"success": False, "error": f"Unknown product: {product_id}", "session_id": None}
    nodes = [n for n in product.get("nodes", []) if n["name"] in node_names] if node_names else product.get("nodes", [])
    if not nodes:
        return {"success": False, "error": "No nodes selected", "session_id": None}
    session_id = str(uuid.uuid4())
    now = datetime.now()
    pattern_type = product.get("log_pattern_type") or get_log_pattern_type()
    import queue as qmod
    session = {
        "records": [],
        "queue": qmod.Queue(),
        "stop": threading.Event(),
        "threads": [],
        "product_id": product_id,
        "node_names": [n["name"] for n in nodes],
    }
    with _sessions_lock:
        _live_sessions[session_id] = session
    threads = []
    for node in nodes:
        log_path = node["log_path"]
        try:
            log_file = now.strftime(node["log_file_pattern"])
        except (ValueError, TypeError):
            log_file = node.get("log_file_pattern", "access_log.%Y-%m-%d").replace("%Y", str(now.year)).replace("%m", f"{now.month:02d}").replace("%d", f"{now.day:02d}")
        t = threading.Thread(target=_ssh_tail_reader, args=(node["hostname"], log_path, log_file, session_id, user_filter, uri_filter, pattern_type, node["name"]), daemon=True)
        t.start()
        threads.append(t)
    session["threads"] = threads
    return {"success": True, "session_id": session_id, "log_file": f"{log_path}/{log_file}", "nodes": [n["name"] for n in nodes]}


def stop_live_session(session_id: str) -> bool:
    """Stop tail threads and remove session."""
    with _sessions_lock:
        session = _live_sessions.get(session_id)
        if not session:
            return False
        session["stop"].set()
        for t in session.get("threads", []):
            if t.is_alive():
                pass  # thread will exit when tail breaks
        del _live_sessions[session_id]
    return True


def get_live_records(session_id: str, since_index: int = 0) -> Dict[str, Any]:
    """Get all records so far and optionally only new ones since index. Also drain queue for new items."""
    with _sessions_lock:
        session = _live_sessions.get(session_id)
        if not session:
            return {"success": False, "records": [], "total": 0, "new_only": []}
        q = session["queue"]
    # Drain queue into session records (already appended in thread; queue has copies for streaming)
    new_from_queue = []
    try:
        while True:
            rec = q.get_nowait()
            if rec is None:
                continue
            if rec.get("error"):
                new_from_queue.append(rec)
            else:
                new_from_queue.append(rec)
    except queue.Empty:
        pass
    with _sessions_lock:
        records = list(_live_sessions.get(session_id, {}).get("records", []))
    if records:
        add_apdex_category(records)
        add_z_scores(records)
    new_only = records[since_index:] if since_index < len(records) else records
    return {"success": True, "records": records, "total": len(records), "new_only": new_only}


def get_live_updates_since(session_id: str, since_index: int) -> List[Dict]:
    """Return records with index >= since_index and recompute z-scores for full list."""
    with _sessions_lock:
        session = _live_sessions.get(session_id)
        if not session:
            return []
        records = list(session["records"])
    if not records:
        return []
    add_apdex_category(records)
    add_z_scores(records)
    return records[since_index:]
