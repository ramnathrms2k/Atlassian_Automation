"""
Jira Project Config Audit — Flask API and browser UI.
Run: python app.py  (listens on port 9000)
"""
import configparser
import json
import os

from flask import Flask, request, jsonify, render_template_string, Response

# Import audit logic (run from package directory)
import jira_audit

app = Flask(__name__)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.ini")

def get_config():
    config = configparser.ConfigParser()
    if not os.path.isfile(CONFIG_PATH):
        return None
    config.read(CONFIG_PATH)
    return config

def get_instances():
    config = get_config()
    if not config:
        return []
    return [s for s in config.sections() if s.upper() != "DEFAULT"]

@app.route("/")
def index():
    instances = get_instances()
    html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Jira Project Config Audit</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 1200px; margin: 2rem auto; padding: 0 1rem; }
    h1 { color: #333; }
    a { color: #0052cc; }
    form { display: flex; gap: 1rem; align-items: flex-end; flex-wrap: wrap; margin-bottom: 1.5rem; }
    label { display: flex; flex-direction: column; gap: 0.25rem; font-weight: 500; }
    input, select { padding: 0.5rem; font-size: 1rem; }
    button { padding: 0.5rem 1rem; background: #0052cc; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
    button:hover { background: #0747a6; }
    #result { margin-top: 1.5rem; }
    .tabs { display: flex; gap: 0.5rem; margin-bottom: 0.5rem; align-items: center; flex-wrap: wrap; }
    .tabs button { background: #ddd; color: #333; }
    .tabs button.active { background: #0052cc; color: #fff; }
    .tabs .btn-download { margin-left: 0.5rem; background: #6b778c; color: #fff; font-size: 0.9rem; }
    .tabs .btn-download:hover { background: #42526e; }
    .tabs .btn-download:disabled { opacity: 0.5; cursor: not-allowed; }
    .panel { display: none; }
    .panel.active { display: block; }
    pre { background: #f4f5f7; padding: 1rem; overflow: auto; max-height: 70vh; border-radius: 4px; white-space: pre-wrap; }
    .error { color: #bf2600; }
    .audit-summary { overflow: auto; max-height: 80vh; font-size: 0.9rem; background: #fafbfc; padding: 1rem; border-radius: 8px; }
    .audit-summary .summary-header { background: linear-gradient(135deg, #172b4d 0%, #253858 100%); color: #fff; padding: 1.25rem 1.5rem; margin: -1rem -1rem 1.25rem -1rem; border-radius: 8px 8px 0 0; box-shadow: 0 2px 4px rgba(0,0,0,0.08); }
    .audit-summary .summary-header h2 { margin: 0; font-size: 1.2rem; font-weight: 600; letter-spacing: 0.02em; }
    .audit-summary .summary-project { margin: 0.4rem 0 0; opacity: 0.95; font-size: 1rem; }
    .audit-summary .summary-section { background: #fff; border: 1px solid #dfe1e6; border-radius: 8px; margin-bottom: 1.25rem; box-shadow: 0 1px 2px rgba(9,30,66,0.06); }
    .audit-summary .summary-section > summary { cursor: pointer; list-style: none; padding: 1.25rem 1.5rem; }
    .audit-summary .summary-section > summary::-webkit-details-marker { display: none; }
    .audit-summary .summary-section > summary h3 { margin: 0; font-size: 1rem; font-weight: 600; color: #172b4d; padding-bottom: 0; border-bottom: none; }
    .audit-summary .summary-section .section-content { padding: 0.75rem 1.5rem 1.25rem; border-top: 1px solid #f4f5f7; }
    .audit-summary .summary-section[open] > summary { border-bottom: 1px solid #deebff; padding-bottom: 0.75rem; margin-bottom: 0; }
    .audit-summary .summary-custom-fields-table .cf-values-cell { max-width: 40rem; word-wrap: break-word; overflow-wrap: break-word; white-space: normal; }
    .audit-summary .summary-screens-fields { border-left: 4px solid #0052cc; }
    .audit-summary table { border-collapse: collapse; width: 100%; font-size: 0.875rem; }
    .audit-summary th, .audit-summary td { border: 1px solid #dfe1e6; padding: 0.4rem 0.6rem; text-align: left; word-wrap: break-word; overflow-wrap: break-word; min-width: 0; box-sizing: border-box; }
    .audit-summary th { background: #f4f5f7; color: #172b4d; font-weight: 600; }
    .audit-summary tbody tr:nth-child(even) { background: #fafbfc; }
    .audit-summary tbody tr:hover { background: #deebff; }
    .audit-summary .req-required { font-weight: 600; color: #0065ff; }
    .audit-summary .req-optional { color: #6b778c; }
    .audit-summary .state-enabled { color: #00875a; font-weight: 500; }
    .audit-summary .state-disabled { color: #6b778c; }
    .audit-summary .summary-automation { overflow-x: hidden; }
    .audit-summary .summary-automation table { table-layout: fixed; width: 100%; }
    .audit-summary .summary-automation th:nth-child(1), .audit-summary .summary-automation td:nth-child(1) { width: 22%; max-width: 22%; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; min-width: 0; vertical-align: top; }
    .audit-summary .summary-automation th:nth-child(2), .audit-summary .summary-automation td:nth-child(2) { width: 8%; max-width: 8%; white-space: normal; min-width: 0; vertical-align: top; }
    .audit-summary .summary-automation th:nth-child(3), .audit-summary .summary-automation td:nth-child(3) { width: 14%; max-width: 14%; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; min-width: 0; vertical-align: top; }
    .audit-summary .summary-automation th:nth-child(4), .audit-summary .summary-automation td:nth-child(4),
    .audit-summary .summary-automation th:nth-child(5), .audit-summary .summary-automation td:nth-child(5) {
      width: 28%; max-width: 28%; white-space: normal; word-wrap: break-word; overflow-wrap: break-word;
      min-height: 2.5em; vertical-align: top; padding: 0.5rem 0.6rem; box-sizing: border-box;
    }
    .audit-summary .screens-fields-table { font-size: 0.8rem; }
    .audit-summary .screens-fields-table th, .audit-summary .screens-fields-table td { padding: 0.3rem 0.5rem; }
    .audit-summary code { background: #eaecef; padding: 0.15rem 0.35rem; border-radius: 3px; font-size: 0.85em; color: #172b4d; }
    .audit-summary .summary-workflow-details { border-left: 4px solid #6554c0; }
    .audit-summary .workflow-details-intro { margin-bottom: 1rem; color: #42526e; font-size: 0.9rem; }
    .audit-summary .workflow-block { margin-bottom: 1.5rem; }
    .audit-summary .workflow-block h4 { margin: 0.5rem 0 0.5rem; font-size: 0.95rem; color: #172b4d; }
    .audit-summary .workflow-issue-types { font-weight: normal; color: #6b778c; }
    .audit-summary .workflow-steps-table, .audit-summary .workflow-transitions-table { margin-bottom: 0.75rem; font-size: 0.8rem; }
    .audit-summary .workflow-steps-table-wrapper, .audit-summary .workflow-transitions-table-wrapper { overflow-x: auto; }
    .audit-summary .workflow-steps-table th:nth-child(1), .audit-summary .workflow-steps-table td:nth-child(1) { position: sticky; left: 0; background: #f4f5f7; z-index: 1; min-width: 4.5rem; box-shadow: 2px 0 2px -1px rgba(0,0,0,0.06); }
    .audit-summary .workflow-steps-table th:nth-child(2), .audit-summary .workflow-steps-table td:nth-child(2) { position: sticky; left: 4.5rem; background: #fff; z-index: 1; min-width: 8rem; box-shadow: 2px 0 2px -1px rgba(0,0,0,0.06); }
    .audit-summary .workflow-steps-table tbody tr:nth-child(even) td:nth-child(1) { background: #f4f5f7; }
    .audit-summary .workflow-steps-table tbody tr:nth-child(even) td:nth-child(2) { background: #fafbfc; }
    .audit-summary .workflow-transitions-table th:nth-child(1), .audit-summary .workflow-transitions-table td:nth-child(1) { position: sticky; left: 0; background: #f4f5f7; z-index: 1; min-width: 7rem; box-shadow: 2px 0 2px -1px rgba(0,0,0,0.06); }
    .audit-summary .workflow-transitions-table th:nth-child(2), .audit-summary .workflow-transitions-table td:nth-child(2) { position: sticky; left: 7rem; background: #fff; z-index: 1; min-width: 4.5rem; box-shadow: 2px 0 2px -1px rgba(0,0,0,0.06); }
    .audit-summary .workflow-transitions-table tbody tr:nth-child(even) td:nth-child(1) { background: #f4f5f7; }
    .audit-summary .workflow-transitions-table tbody tr:nth-child(even) td:nth-child(2) { background: #fafbfc; }
    .audit-summary .workflow-xml-details { margin-top: 0.75rem; border: 1px solid #dfe1e6; border-radius: 6px; overflow: hidden; }
    .audit-summary .workflow-xml-details summary { cursor: pointer; font-weight: 600; color: #0052cc; padding: 0.5rem 0.75rem; background: #f4f5f7; list-style: none; }
    .audit-summary .workflow-xml-details summary::-webkit-details-marker { display: none; }
    .audit-summary .workflow-xml-details[open] summary { border-bottom: 1px solid #dfe1e6; }
    .audit-summary .workflow-xml-pre { max-height: 300px; overflow: auto; font-size: 0.75rem; white-space: pre-wrap; word-break: break-all; background: #f4f5f7; padding: 0.5rem; border-radius: 0 0 6px 6px; margin: 0; }
    .audit-summary .workflow-parse-warn { color: #de350b; font-size: 0.85rem; margin: 0.25rem 0; }
  </style>
</head>
<body>
  <h1>Jira Project Config Audit</h1>
  <p>Run an audit for a project and view the summary or full JSON.</p>
  <form id="auditForm">
    <label>
      Instance
      <select name="instance" required>
        <option value="">— Select —</option>
        """ + "".join(f'<option value="{i}">{i}</option>' for i in instances) + """
      </select>
    </label>
    <label>
      Project key
      <input type="text" name="project" placeholder="e.g. UAT1ESX" required>
    </label>
    <button type="submit">Run audit</button>
  </form>
  <div id="result" style="display: none;">
    <div class="tabs">
      <button type="button" data-tab="summary" class="active">Summary</button>
      <button type="button" data-tab="json">JSON</button>
      <button type="button" id="btnDownloadHtml" class="btn-download" disabled title="Download current summary as HTML file">Download summary (HTML)</button>
      <button type="button" id="btnDownloadJson" class="btn-download" disabled title="Download current audit as JSON file">Download JSON</button>
    </div>
    <div id="panel-summary" class="panel active"><div id="summaryHtml" class="audit-summary"></div><pre id="summaryText" style="display:none;"></pre></div>
    <div id="panel-json" class="panel"><pre id="jsonText"></pre></div>
  </div>
  <script>
    const form = document.getElementById('auditForm');
    const result = document.getElementById('result');
    const summaryHtml = document.getElementById('summaryHtml');
    const summaryPre = document.getElementById('summaryText');
    const jsonPre = document.getElementById('jsonText');
    const tabs = document.querySelectorAll('.tabs button[data-tab]');
    const panels = document.querySelectorAll('.panel');
    const btnDownloadHtml = document.getElementById('btnDownloadHtml');
    const btnDownloadJson = document.getElementById('btnDownloadJson');
    let lastAudit = null;

    function downloadBlob(blob, filename) {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      a.click();
      URL.revokeObjectURL(a.href);
    }

    btnDownloadHtml.addEventListener('click', () => {
      if (!lastAudit || !lastAudit.summary_html) return;
      const doc = '<!DOCTYPE html><html><head><meta charset="utf-8"><title>Audit summary – ' + (lastAudit.instance + '-' + lastAudit.project) + '</title><style>.audit-summary{font-family:system-ui,sans-serif;max-width:1200px;margin:0 auto;padding:1rem;font-size:0.9rem;}.audit-summary .summary-header{background:linear-gradient(135deg,#172b4d 0%,#253858 100%);color:#fff;padding:1.25rem 1.5rem;margin:-1rem -1rem 1.25rem -1rem;border-radius:8px 8px 0 0;}.audit-summary .summary-section{background:#fff;border:1px solid #dfe1e6;border-radius:8px;margin-bottom:1rem;}.audit-summary .summary-section>summary{cursor:pointer;list-style:none;padding:1rem 1.25rem;}.audit-summary .summary-section>summary::-webkit-details-marker{display:none;}.audit-summary .summary-section .section-content{padding:0.75rem 1.25rem 1rem;border-top:1px solid #f4f5f7;}.audit-summary table{border-collapse:collapse;width:100%;}.audit-summary th,.audit-summary td{border:1px solid #dfe1e6;padding:0.4rem 0.6rem;text-align:left;word-wrap:break-word;}.audit-summary th{background:#f4f5f7;}.audit-summary code{background:#eaecef;padding:0.15rem 0.35rem;border-radius:3px;}.audit-summary .cf-values-cell{max-width:40rem;word-wrap:break-word;overflow-wrap:break-word;}</style></head><body><div class="audit-summary">' + lastAudit.summary_html + '</div></body></html>';
      const blob = new Blob([doc], { type: 'text/html;charset=utf-8' });
      downloadBlob(blob, 'audit-summary-' + lastAudit.instance + '-' + lastAudit.project + '.html');
    });

    btnDownloadJson.addEventListener('click', () => {
      if (!lastAudit || !lastAudit.snapshot) return;
      const str = JSON.stringify(lastAudit.snapshot, null, 2);
      const blob = new Blob([str], { type: 'application/json;charset=utf-8' });
      downloadBlob(blob, 'audit-snapshot-' + lastAudit.instance + '-' + lastAudit.project + '.json');
    });

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const instance = form.instance.value;
      const project = form.project.value.trim();
      if (!instance || !project) return;
      lastAudit = null;
      btnDownloadHtml.disabled = true;
      btnDownloadJson.disabled = true;
      summaryHtml.innerHTML = '<p>Loading…</p>';
      summaryPre.textContent = 'Loading…';
      jsonPre.textContent = 'Loading…';
      result.style.display = 'block';
      document.querySelector('#panel-summary').classList.add('active');
      document.querySelector('#panel-json').classList.remove('active');
      tabs[0].classList.add('active');
      if (tabs[1]) tabs[1].classList.remove('active');
      try {
        const r = await fetch('/api/audit?instance=' + encodeURIComponent(instance) + '&project=' + encodeURIComponent(project));
        const data = await r.json();
        if (!r.ok) {
          summaryHtml.innerHTML = '';
          summaryPre.style.display = 'block';
          summaryPre.textContent = data.error || 'Request failed';
          jsonPre.textContent = JSON.stringify(data, null, 2);
          return;
        }
        lastAudit = { summary_html: data.summary_html || '', summary: data.summary || '', snapshot: data.snapshot, instance: instance, project: project };
        btnDownloadHtml.disabled = false;
        btnDownloadJson.disabled = false;
        if (data.summary_html) {
          summaryHtml.innerHTML = data.summary_html;
          summaryHtml.style.display = 'block';
          summaryPre.style.display = 'none';
        } else {
          summaryHtml.style.display = 'none';
          summaryPre.style.display = 'block';
          summaryPre.textContent = data.summary || '';
        }
        jsonPre.textContent = JSON.stringify(data.snapshot, null, 2);
      } catch (err) {
        summaryHtml.innerHTML = '';
        summaryPre.style.display = 'block';
        summaryPre.textContent = 'Error: ' + err.message;
        jsonPre.textContent = '';
      }
    });

    tabs.forEach(btn => {
      btn.addEventListener('click', () => {
        const t = btn.dataset.tab;
        tabs.forEach(b => b.classList.remove('active'));
        panels.forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('panel-' + t).classList.add('active');
      });
    });
  </script>
</body>
</html>"""
    return render_template_string(html)

@app.route("/api/audit")
def api_audit():
    """GET /api/audit?instance=SBX&project=UAT1ESX — returns { summary, summary_html, snapshot }."""
    instance = request.args.get("instance", "").strip()
    project = request.args.get("project", "").strip()
    if not instance or not project:
        return jsonify({"error": "Missing instance or project"}), 400
    config = get_config()
    if not config or instance not in config:
        return jsonify({"error": f"Unknown instance: {instance}"}), 400
    try:
        snapshot = jira_audit.run_audit(config, instance, project)
        summary = jira_audit.build_audit_summary(snapshot)
        summary_html = jira_audit.build_audit_summary_html(snapshot)
        raw = json.dumps(snapshot, indent=2, default=jira_audit.json_serial)
        snapshot_clean = json.loads(raw)
        return jsonify({"summary": summary, "summary_html": summary_html, "snapshot": snapshot_clean})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audit/html")
def api_audit_html():
    """GET /api/audit/html?instance=SBX&project=UAT1ESX — returns HTML summary only."""
    instance = request.args.get("instance", "").strip()
    project = request.args.get("project", "").strip()
    if not instance or not project:
        return Response("Missing instance or project", status=400, mimetype="text/html")
    config = get_config()
    if not config or instance not in config:
        return Response(f"Unknown instance: {instance}", status=400, mimetype="text/html")
    try:
        snapshot = jira_audit.run_audit(config, instance, project)
        summary_html = jira_audit.build_audit_summary_html(snapshot)
        return Response(summary_html, mimetype="text/html; charset=utf-8")
    except Exception as e:
        return Response(str(e), status=500, mimetype="text/html")

@app.route("/api/audit/summary")
def api_audit_summary():
    """GET /api/audit/summary?instance=SBX&project=UAT1ESX — returns text/plain summary."""
    instance = request.args.get("instance", "").strip()
    project = request.args.get("project", "").strip()
    if not instance or not project:
        return Response("Missing instance or project", status=400, mimetype="text/plain")
    config = get_config()
    if not config or instance not in config:
        return Response(f"Unknown instance: {instance}", status=400, mimetype="text/plain")
    try:
        snapshot = jira_audit.run_audit(config, instance, project)
        summary = jira_audit.build_audit_summary(snapshot)
        return Response(summary, mimetype="text/plain; charset=utf-8")
    except Exception as e:
        return Response(str(e), status=500, mimetype="text/plain")

@app.route("/api/compare")
def api_compare():
    """GET /api/compare?instance1=SBX&project1=UAT1ESX&instance2=PRD&project2=UAT1ESX — returns { left, right } with summary_html and snapshot each."""
    i1 = request.args.get("instance1", "").strip()
    p1 = request.args.get("project1", "").strip()
    i2 = request.args.get("instance2", "").strip()
    p2 = request.args.get("project2", "").strip()
    if not all([i1, p1, i2, p2]):
        return jsonify({"error": "Missing instance1, project1, instance2, or project2"}), 400
    config = get_config()
    if not config:
        return jsonify({"error": "No config"}), 500
    for inst in (i1, i2):
        if inst not in config:
            return jsonify({"error": f"Unknown instance: {inst}"}), 400
    try:
        snap1 = jira_audit.run_audit(config, i1, p1)
        snap2 = jira_audit.run_audit(config, i2, p2)
        raw1 = json.dumps(snap1, indent=2, default=jira_audit.json_serial)
        raw2 = json.dumps(snap2, indent=2, default=jira_audit.json_serial)
        return jsonify({
            "left": {
                "instance": i1, "project": p1,
                "summary_html": jira_audit.build_audit_summary_html(snap1),
                "snapshot": json.loads(raw1),
            },
            "right": {
                "instance": i2, "project": p2,
                "summary_html": jira_audit.build_audit_summary_html(snap2),
                "snapshot": json.loads(raw2),
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/audit/json")
def api_audit_json():
    """GET /api/audit/json?instance=SBX&project=UAT1ESX — returns application/json snapshot."""
    instance = request.args.get("instance", "").strip()
    project = request.args.get("project", "").strip()
    if not instance or not project:
        return jsonify({"error": "Missing instance or project"}), 400
    config = get_config()
    if not config or instance not in config:
        return jsonify({"error": f"Unknown instance: {instance}"}), 400
    try:
        snapshot = jira_audit.run_audit(config, instance, project)
        raw = json.dumps(snapshot, indent=2, default=jira_audit.json_serial)
        return Response(raw, mimetype="application/json; charset=utf-8")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/compare")
def compare_page():
    """Compare two audits side by side (same project in two envs or two different projects)."""
    instances = get_instances()
    opts = "".join(f'<option value="{i}">{i}</option>' for i in instances)
    html = """<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Compare Audits — Jira Project Config</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 2rem; padding: 0 1rem; }
    h1 { color: #333; }
    a { color: #0052cc; }
    .compare-wrap { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; max-width: 1600px; margin: 0 auto; }
    @media (max-width: 900px) { .compare-wrap { grid-template-columns: 1fr; } }
    .col { border: 1px solid #ddd; border-radius: 8px; padding: 1rem; background: #fafafa; }
    .col h2 { margin: 0 0 1rem; font-size: 1rem; }
    .col form { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: flex-end; margin-bottom: 1rem; }
    .col label { display: flex; flex-direction: column; gap: 0.2rem; font-size: 0.9rem; }
    .col input, .col select { padding: 0.4rem; }
    .col button { padding: 0.4rem 0.8rem; background: #0052cc; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
    .col .result { background: #fafbfc; border: 1px solid #dfe1e6; border-radius: 8px; padding: 0.75rem; overflow: auto; max-height: 78vh; font-size: 0.85rem; }
    .col .result .audit-summary { max-height: none; padding: 0.5rem 0; }
    .col .result .summary-header { background: linear-gradient(135deg, #172b4d 0%, #253858 100%); color: #fff; padding: 0.75rem 1rem; margin: -0.75rem -0.75rem 1rem -0.75rem; border-radius: 8px 8px 0 0; }
    .col .result .summary-header h2 { margin: 0; font-size: 1rem; font-weight: 600; }
    .col .result .summary-project { margin: 0.25rem 0 0; opacity: 0.95; font-size: 0.9rem; }
    .col .result .summary-section { background: #fff; border: 1px solid #dfe1e6; border-radius: 8px; margin-bottom: 1rem; box-shadow: 0 1px 2px rgba(9,30,66,0.06); }
    .col .result .summary-section > summary { cursor: pointer; list-style: none; padding: 0.75rem 1rem; }
    .col .result .summary-section > summary::-webkit-details-marker { display: none; }
    .col .result .summary-section > summary h3 { margin: 0; font-size: 0.95rem; font-weight: 600; color: #172b4d; padding-bottom: 0; border-bottom: none; }
    .col .result .summary-section .section-content { padding: 0 1rem 0.75rem; border-top: 1px solid #f4f5f7; }
    .col .result .summary-section[open] > summary { border-bottom: 1px solid #deebff; padding-bottom: 0.5rem; }
    .col .result .summary-custom-fields-table .cf-values-cell { max-width: 30rem; word-wrap: break-word; overflow-wrap: break-word; white-space: normal; }
    .col .result .summary-screens-fields { border-left: 4px solid #0052cc; }
    .col .result table { border-collapse: collapse; width: 100%; margin-bottom: 0; font-size: 0.8rem; }
    .col .result th, .col .result td { border: 1px solid #dfe1e6; padding: 0.3rem 0.5rem; text-align: left; word-wrap: break-word; overflow-wrap: break-word; min-width: 0; box-sizing: border-box; }
    .col .result th { background: #f4f5f7; color: #172b4d; font-weight: 600; }
    .col .result tbody tr:nth-child(even) { background: #fafbfc; }
    .col .result tbody tr:hover { background: #deebff; }
    .col .result .req-required { font-weight: 600; color: #0065ff; }
    .col .result .req-optional { color: #6b778c; }
    .col .result .state-enabled { color: #00875a; }
    .col .result .state-disabled { color: #6b778c; }
    .col .result .summary-automation { overflow-x: hidden; }
    .col .result .summary-automation table { table-layout: fixed; width: 100%; }
    .col .result .summary-automation th:nth-child(1), .col .result .summary-automation td:nth-child(1) { width: 22%; max-width: 22%; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; min-width: 0; vertical-align: top; }
    .col .result .summary-automation th:nth-child(2), .col .result .summary-automation td:nth-child(2) { width: 8%; max-width: 8%; white-space: normal; min-width: 0; vertical-align: top; }
    .col .result .summary-automation th:nth-child(3), .col .result .summary-automation td:nth-child(3) { width: 14%; max-width: 14%; white-space: normal; word-wrap: break-word; overflow-wrap: break-word; min-width: 0; vertical-align: top; }
    .col .result .summary-automation th:nth-child(4), .col .result .summary-automation td:nth-child(4),
    .col .result .summary-automation th:nth-child(5), .col .result .summary-automation td:nth-child(5) {
      width: 28%; max-width: 28%; white-space: normal; word-wrap: break-word; overflow-wrap: break-word;
      min-height: 2.5em; vertical-align: top; padding: 0.4rem 0.5rem; box-sizing: border-box;
    }
    .col .result .screens-fields-table { font-size: 0.75rem; }
    .col .result .screens-fields-table th, .col .result .screens-fields-table td { padding: 0.25rem 0.4rem; }
    .col .result code { background: #eaecef; padding: 0.1rem 0.25rem; border-radius: 3px; font-size: 0.85em; color: #172b4d; }
    .col .result .summary-workflow-details { border-left: 4px solid #6554c0; }
    .col .result .workflow-details-intro { margin-bottom: 0.75rem; font-size: 0.85rem; }
    .col .result .workflow-block { margin-bottom: 1rem; }
    .col .result .workflow-block h4 { margin: 0.4rem 0 0.4rem; font-size: 0.9rem; }
    .col .result .workflow-steps-table, .col .result .workflow-transitions-table { font-size: 0.75rem; }
    .col .result .workflow-steps-table-wrapper, .col .result .workflow-transitions-table-wrapper { overflow-x: auto; }
    .col .result .workflow-steps-table th:nth-child(1), .col .result .workflow-steps-table td:nth-child(1) { position: sticky; left: 0; background: #f4f5f7; z-index: 1; min-width: 4.5rem; }
    .col .result .workflow-steps-table th:nth-child(2), .col .result .workflow-steps-table td:nth-child(2) { position: sticky; left: 4.5rem; background: #fff; z-index: 1; min-width: 8rem; }
    .col .result .workflow-transitions-table th:nth-child(1), .col .result .workflow-transitions-table td:nth-child(1) { position: sticky; left: 0; background: #f4f5f7; z-index: 1; min-width: 7rem; }
    .col .result .workflow-transitions-table th:nth-child(2), .col .result .workflow-transitions-table td:nth-child(2) { position: sticky; left: 7rem; background: #fff; z-index: 1; min-width: 4.5rem; }
    .col .result .workflow-xml-details { margin-top: 0.5rem; border: 1px solid #dfe1e6; border-radius: 6px; }
    .col .result .workflow-xml-details summary { cursor: pointer; font-weight: 600; color: #0052cc; padding: 0.4rem 0.6rem; background: #f4f5f7; }
    .col .result .workflow-xml-pre { max-height: 200px; font-size: 0.7rem; }
    .compare-actions { margin-bottom: 1rem; }
    .compare-actions button { padding: 0.5rem 1rem; background: #0052cc; color: #fff; border: none; border-radius: 4px; cursor: pointer; }
    .compare-actions button:hover { background: #0747a6; }
    .loading { color: #666; }
    .err { color: #bf2600; }
  </style>
</head>
<body>
  <h1>Compare Audits</h1>
  <p>Compare the same project between two environments (e.g. SBX vs PRD) or two different projects. <a href="/">Single audit</a></p>
  <details style="margin-bottom: 1rem; padding: 0.75rem; background: #f4f5f7; border-radius: 4px;">
    <summary style="cursor: pointer; font-weight: 600;">How to compare (step-by-step)</summary>
    <ol style="margin: 0.5rem 0 0 1.2rem; padding: 0;">
      <li><strong>Same project, two environments:</strong> Left = Instance <code>SBX</code>, Project <code>UAT1ESX</code>; Right = Instance <code>PRD</code>, Project <code>UAT1ESX</code>. Click <strong>Run both audits</strong> to load both summaries side by side.</li>
      <li><strong>Two different projects:</strong> Set Left and Right to the instances and project keys you want, then click <strong>Run both audits</strong>.</li>
      <li><strong>Single column:</strong> Use <strong>Run left</strong> or <strong>Run right</strong> on one side only to load that audit in that column.</li>
      <li>Scroll each column to compare Schemes, Automation Rules, ScriptRunner Behaviors, Permission Details, Screens and Fields, and Custom Field Options.</li>
    </ol>
  </details>
  <div class="compare-actions">
    <button type="button" id="runBoth">Run both audits</button>
  </div>
  <div class="compare-wrap">
    <div class="col">
      <h2>Left (e.g. Sandbox)</h2>
      <form id="formLeft">
        <label>Instance <select name="instance">""" + opts + """</select></label>
        <label>Project <input type="text" name="project" placeholder="UAT1ESX" required></label>
        <button type="submit">Run left</button>
      </form>
      <div id="resultLeft" class="result"></div>
    </div>
    <div class="col">
      <h2>Right (e.g. Production)</h2>
      <form id="formRight">
        <label>Instance <select name="instance">""" + opts + """</select></label>
        <label>Project <input type="text" name="project" placeholder="UAT1ESX" required></label>
        <button type="submit">Run right</button>
      </form>
      <div id="resultRight" class="result"></div>
    </div>
  </div>
  <script>
    const resultLeft = document.getElementById('resultLeft');
    const resultRight = document.getElementById('resultRight');
    const formLeft = document.getElementById('formLeft');
    const formRight = document.getElementById('formRight');
    const runBoth = document.getElementById('runBoth');

    function runOne(instance, project, el) {
      el.innerHTML = '<span class="loading">Loading…</span>';
      const q = 'instance=' + encodeURIComponent(instance) + '&project=' + encodeURIComponent(project);
      fetch('/api/audit?' + q).then(r => r.json()).then(data => {
        if (data.error) { el.innerHTML = '<span class="err">' + data.error + '</span>'; return; }
        el.innerHTML = data.summary_html || ('<pre>' + (data.summary || '').replace(/</g, '&lt;') + '</pre>');
      }).catch(err => { el.innerHTML = '<span class="err">' + err.message + '</span>'; });
    }

    function runCompare() {
      const i1 = formLeft.instance.value;
      const p1 = formLeft.project.value.trim();
      const i2 = formRight.instance.value;
      const p2 = formRight.project.value.trim();
      if (!i1 || !p1 || !i2 || !p2) return;
      resultLeft.innerHTML = '<span class="loading">Loading left…</span>';
      resultRight.innerHTML = '<span class="loading">Loading right…</span>';
      const q = 'instance1=' + encodeURIComponent(i1) + '&project1=' + encodeURIComponent(p1) +
                '&instance2=' + encodeURIComponent(i2) + '&project2=' + encodeURIComponent(p2);
      fetch('/api/compare?' + q).then(r => r.json()).then(data => {
        if (data.error) {
          resultLeft.innerHTML = resultRight.innerHTML = '<span class="err">' + data.error + '</span>';
          return;
        }
        resultLeft.innerHTML = data.left.summary_html;
        resultRight.innerHTML = data.right.summary_html;
      }).catch(err => {
        resultLeft.innerHTML = resultRight.innerHTML = '<span class="err">' + err.message + '</span>';
      });
    }

    formLeft.addEventListener('submit', e => { e.preventDefault(); runOne(formLeft.instance.value, formLeft.project.value.trim(), resultLeft); });
    formRight.addEventListener('submit', e => { e.preventDefault(); runOne(formRight.instance.value, formRight.project.value.trim(), resultRight); });
    runBoth.addEventListener('click', runCompare);
  </script>
</body>
</html>"""
    return render_template_string(html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9000, debug=False)
