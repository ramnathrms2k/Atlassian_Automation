"""
Flask app for Response Time Analysis: on-demand and live mode.
Port 9090. Config loaded from config/config.yaml.
"""
import json
import logging
from datetime import datetime
from flask import Flask, render_template, request, jsonify, Response, stream_with_context

from load_config import get_products, get_product, get_flask_port, get_default_days, get_default_z_threshold
from analysis import run_on_demand_analysis
from live_tail import start_live_session, stop_live_session, get_live_updates_since

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

app = Flask(__name__)


def _parse_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s.strip()[:10], "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


@app.route("/")
def index():
    products = get_products()
    product_list = [{"id": k, "name": v.get("display_name", k)} for k, v in products.items()]
    nodes_by_product = {k: [n["name"] for n in v.get("nodes", [])] for k, v in products.items()}
    return render_template(
        "index.html",
        product_list=product_list,
        nodes_by_product=json.dumps(nodes_by_product),
        default_days=get_default_days(),
        default_z_threshold=get_default_z_threshold(),
    )


@app.route("/api/analyze", methods=["POST"])
def api_analyze():
    """On-demand analysis. JSON body: product_id, node_names[], from_date, to_date, days, user_filter, uri_filter, cumulative."""
    data = request.get_json(force=True, silent=True) or {}
    product_id = (data.get("product_id") or "").strip() or None
    if not product_id:
        return jsonify({"success": False, "error": "product_id required"}), 400
    node_names = data.get("node_names") or []
    from_date = _parse_date(data.get("from_date"))
    to_date = _parse_date(data.get("to_date"))
    days = data.get("days")
    if days is not None:
        try:
            days = int(days)
        except (TypeError, ValueError):
            days = get_default_days()
    else:
        days = get_default_days()
    user_filter = (data.get("user_filter") or "").strip() or None
    uri_filter = (data.get("uri_filter") or "").strip() or None
    cumulative = data.get("cumulative", True)
    result = run_on_demand_analysis(
        product_id=product_id,
        node_names=node_names if node_names else None,
        from_date=from_date,
        to_date=to_date,
        days=days,
        user_filter=user_filter,
        uri_filter=uri_filter,
        cumulative=cumulative,
    )
    if not result.get("success"):
        return jsonify(result), 400
    # For JSON response: return table rows and chart data
    records = result.get("cumulative") if cumulative else []
    if not cumulative:
        for node_name, recs in result.get("per_node", {}).items():
            records.extend(recs)
        records.sort(key=lambda r: (r.get("timestamp") or "", r.get("node") or ""))
    table_rows = []
    for r in records:
        row = {
            "timestamp": r.get("timestamp"),
            "node": r.get("node"),
            "user": r.get("user"),
            "uri": r.get("uri_full") or r.get("uri"),
            "response_time_ms": r.get("response_time_ms"),
            "z_score": r.get("z_score"),
            "apdex_category": r.get("apdex_category"),
        }
        table_rows.append(row)
    # Chart data: time series of response_time_ms and z_score
    labels = [r.get("timestamp") or "" for r in records]
    response_times = [r.get("response_time_ms") for r in records]
    z_scores = [r.get("z_score") for r in records]
    summary = result.get("summary") or {}
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"response_time_{product_id}_{days}d_{ts}.csv"
    return jsonify({
        "success": True,
        "table_rows": table_rows,
        "chart": {
            "labels": labels,
            "response_time_ms": response_times,
            "z_score": z_scores,
        },
        "summary": summary,
        "csv": result.get("csv_string", ""),
        "per_node_summary": result.get("per_node_summary", {}),
        "csv_filename": csv_filename,
        "per_node": {k: v for k, v in result.get("per_node", {}).items()},
        "cumulative": cumulative,
    })


@app.route("/api/csv", methods=["POST"])
def api_csv():
    """Return CSV only (same inputs as /api/analyze)."""
    data = request.get_json(force=True, silent=True) or {}
    product_id = (data.get("product_id") or "").strip()
    if not product_id:
        return Response("product_id required", status=400, mimetype="text/plain")
    node_names = data.get("node_names") or []
    from_date = _parse_date(data.get("from_date"))
    to_date = _parse_date(data.get("to_date"))
    days = data.get("days", get_default_days())
    try:
        days = int(days)
    except (TypeError, ValueError):
        days = get_default_days()
    user_filter = (data.get("user_filter") or "").strip() or None
    uri_filter = (data.get("uri_filter") or "").strip() or None
    cumulative = data.get("cumulative", True)
    result = run_on_demand_analysis(
        product_id=product_id,
        node_names=node_names if node_names else None,
        from_date=from_date,
        to_date=to_date,
        days=days,
        user_filter=user_filter,
        uri_filter=uri_filter,
        cumulative=cumulative,
    )
    if not result.get("success"):
        return Response(result.get("error", "Error"), status=400, mimetype="text/plain")
    return Response(result.get("csv_string", ""), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=response_time_analysis.csv"})


# --- Live mode ---
@app.route("/api/live/start", methods=["POST"])
def api_live_start():
    data = request.get_json(force=True, silent=True) or {}
    product_id = (data.get("product_id") or "").strip()
    if not product_id:
        return jsonify({"success": False, "error": "product_id required"}), 400
    node_names = data.get("node_names") or []
    user_filter = (data.get("user_filter") or "").strip() or None
    uri_filter = (data.get("uri_filter") or "").strip() or None
    out = start_live_session(product_id, node_names, user_filter=user_filter, uri_filter=uri_filter)
    if not out.get("success"):
        return jsonify(out), 400
    return jsonify(out)


@app.route("/api/live/stop/<session_id>", methods=["POST"])
def api_live_stop(session_id):
    ok = stop_live_session(session_id)
    return jsonify({"success": ok})


@app.route("/api/live/updates/<session_id>")
def api_live_updates(session_id):
    """Poll for new records since index. Query param: since=0."""
    since = request.args.get("since", "0")
    try:
        since = int(since)
    except ValueError:
        since = 0
    data = get_live_updates_since(session_id, since)
    return jsonify({"success": True, "records": data, "count": len(data)})


@app.route("/api/live/full/<session_id>")
def api_live_full(session_id):
    """Get full record list for session (for initial load and z-score)."""
    from live_tail import _live_sessions, _sessions_lock
    with _sessions_lock:
        session = _live_sessions.get(session_id)
        if not session:
            return jsonify({"success": False, "records": []}), 404
        records = list(session.get("records", []))
    if records:
        from parser import add_z_scores, add_apdex_category
        add_apdex_category(records)
        add_z_scores(records)
    return jsonify({"success": True, "records": records})


def main():
    port = get_flask_port()
    logger.info("Starting Response Time Analysis on port %s", port)
    app.run(host="0.0.0.0", port=port, debug=True, threaded=True)


if __name__ == "__main__":
    main()
