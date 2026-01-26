import subprocess
import os
import re
import difflib
import datetime
from flask import Flask, render_template, jsonify, request
import config

app = Flask(__name__)

# Ensure reports directory exists
if not os.path.exists(config.REPORT_DIR):
    os.makedirs(config.REPORT_DIR)

def ansi_to_html(text):
    """Converts ANSI colors to HTML for the node tabs"""
    COLOR_MAP = {
        '\x1b[31m': '<span style="color: #ff5555;">', 
        '\x1b[32m': '<span style="color: #50fa7b;">', 
        '\x1b[33m': '<span style="color: #f1fa8c;">', 
        '\x1b[34m': '<span style="color: #bd93f9;">', 
        '\x1b[35m': '<span style="color: #ff79c6;">', 
        '\x1b[36m': '<span style="color: #8be9fd;">', 
        '\x1b[1m':  '<span style="font-weight: bold;">', 
        '\x1b[0m':  '</span>'
    }
    for ansi, html in COLOR_MAP.items():
        text = text.replace(ansi, html)
    return text

def extract_identity(text):
    """Parses the raw report to extract 'Identity' markers"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    clean = ansi_escape.sub('', text)
    identity = {}
    
    # Extract Identity Values
    m_host = re.search(r'Hostname:([^|]+)', clean)
    identity['Hostname'] = m_host.group(1) if m_host else "Unknown"

    m_node = re.search(r'Node ID\s+:\s+(.*)', clean)
    identity['Node ID'] = m_node.group(1).strip() if m_node else "Unknown"

    m_shared = re.search(r'Shared Home\s+:\s+(.*?)(\[|$)', clean)
    identity['Shared Home'] = m_shared.group(1).strip() if m_shared else "Unknown"
    
    m_db = re.search(r'DB Host/Port\s+:\s+(.*)', clean)
    identity['DB Connection'] = m_db.group(1).strip() if m_db else "Unknown"

    return identity

def generate_identity_table(name_a, id_a, name_b, id_b):
    """Generates the HTML Table for Section 1 with Source Hints"""
    
    # Define Rows: (Label, SourceFile)
    rows = [
        ('Hostname', ''),
        ('Node ID', 'cluster.properties'),
        ('Shared Home', 'cluster.properties'),
        ('DB Connection', 'dbconfig.xml')
    ]
    
    html = "<div class='card mb-4 shadow-sm'>"
    html += "<div class='card-header bg-secondary text-white fw-bold'>🔹 Section 1: Identity & Topology Matrix (Expected Drift)</div>"
    html += "<div class='card-body p-0'>"
    html += "<table class='table table-striped mb-0 table-bordered'>"
    html += f"<thead class='table-light'><tr><th style='width:25%'>Config Item</th><th style='width:37%'>{name_a} (Ref)</th><th style='width:37%'>{name_b} (Target)</th></tr></thead>"
    html += "<tbody>"
    
    for label, source_file in rows:
        val_a = id_a.get(label, 'N/A')
        val_b = id_b.get(label, 'N/A')
        
        # Build the Label Column with Source Hint
        label_html = f"<strong>{label}</strong>"
        if source_file:
            # Non-bold, small font, grey color (text-muted)
            label_html += f"<br><span class='text-muted small fw-normal' style='font-size:0.85em;'>({source_file})</span>"

        # Styling Logic
        row_style = ""
        
        if label == 'Node ID' and val_a == val_b and name_a != name_b:
            # Collision Danger
            val_b = f"<span class='badge bg-danger'>COLLISION: {val_b}</span>"
            row_style = "class='table-danger'"
        elif val_a != val_b:
            # Expected Difference
            val_b = f"<span class='text-primary fw-bold'>{val_b}</span>"
        else:
            # Identical
            val_b = f"<span class='text-muted'>{val_b}</span>"

        html += f"<tr {row_style}><td>{label_html}</td><td class='text-break'>{val_a}</td><td class='text-break'>{val_b}</td></tr>"
    
    html += "</tbody></table></div></div>"
    return html

def normalize_for_diff(text_output):
    """Pass 2: Strips noise so we can compare pure configuration state"""
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    clean_text = ansi_escape.sub('', text_output)
    lines = clean_text.splitlines()
    normalized = []
    in_cluster_table = False

    for line in lines:
        s = line.strip()
        if any(s.startswith(x) for x in ["Authenticated to", "Transferred:", "Bytes per second:", "REPORT_METADATA_START"]): continue
        if any(x in line for x in ["Date:", "Hostname:", "Source:", "Report saved to:"]): continue
        
        if "Node ID" in line and ":" in line: line = re.sub(r'(Node ID\s+:\s+).*', r'\1<MASKED_IDENTITY>', line)
        if "Shared Home" in line and ":" in line: line = re.sub(r'(Shared Home\s+:\s+).*', r'\1<MASKED_IDENTITY>', line)
        
        if "Disk Space" in line and ":" in line: line = re.sub(r'(Disk Space.*:\s+).*', r'\1<IGNORED_DYNAMIC>', line)
        
        if "Node ID" in line and "State" in line: in_cluster_table = True; continue
        if "Cluster Query" in line and "Success" in line: in_cluster_table = False
        if in_cluster_table: continue

        normalized.append(line)
    return normalized

@app.route('/')
def index():
    return render_template('index.html', nodes=config.HOSTS)

@app.route('/validate', methods=['POST'])
def validate_node():
    host = request.json.get('host')
    if host not in config.HOSTS: return jsonify({"output": "Unauthorized"}), 400

    subprocess.run(["scp", "-o", "StrictHostKeyChecking=no", "-q", config.VALIDATOR_SCRIPT, f"{config.SSH_USER}@{host}:/tmp/nv.py"])

    remote_cmd = (
        f"export ATLASSIAN_DB_PASSWORD='{config.DB_PASSWORD}'; "
        f"export JIRA_VERSION='{config.JIRA_VERSION}'; "
        f"export JIRA_INSTALL_DIR='{config.JIRA_INSTALL_DIR}'; "
        f"export DB_VALIDATION_USER='{config.DB_VALIDATION_USER}'; "
        "export FORCE_COLOR=1; " 
        "export SKIP_FILE_WRITE=1; " 
        "python3 /tmp/nv.py; "
        "rm /tmp/nv.py"
    )
    
    ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", f"{config.SSH_USER}@{host}", remote_cmd]
    try:
        res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=60)
        raw_output = res.stdout + res.stderr
    except Exception as e:
        raw_output = f"Error: {e}"

    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{host}_{ts}.txt"
    filepath = os.path.join(config.REPORT_DIR, filename)
    
    ansi_escape = re.compile(r'\x1b\[[0-9;]*m')
    clean_text = ansi_escape.sub('', raw_output)
    with open(filepath, "w") as f: f.write(clean_text)

    return jsonify({"output": ansi_to_html(raw_output), "raw": raw_output})

@app.route('/reports', methods=['GET'])
def list_reports():
    try:
        files = sorted(os.listdir(config.REPORT_DIR), reverse=True)
        return jsonify(files)
    except: return jsonify([])

@app.route('/compare_live', methods=['POST'])
def compare_live():
    data = request.json 
    nodes = list(data.keys())
    if len(nodes) < 2: return jsonify({"diff": "Need 2 nodes."})

    ref_node = nodes[0]
    raw_ref = data[ref_node]
    
    id_ref = extract_identity(raw_ref)
    norm_ref = normalize_for_diff(raw_ref)
    
    final_html = []

    for i in range(1, len(nodes)):
        target_node = nodes[i]
        raw_target = data[target_node]
        
        id_target = extract_identity(raw_target)
        
        # Build Section 1 with Source Hints
        final_html.append(generate_identity_table(ref_node, id_ref, target_node, id_target))
        
        # Build Section 2
        norm_target = normalize_for_diff(raw_target)
        diff = list(difflib.unified_diff(norm_ref, norm_target, fromfile=ref_node, tofile=target_node, lineterm=''))
        
        final_html.append("<div class='card mb-5 shadow-sm border-danger'>")
        final_html.append("<div class='card-header bg-danger text-white fw-bold'>🔸 Section 2: Configuration Drift (Unexpected)</div>")
        
        if not diff:
            final_html.append("<div class='card-body bg-light text-success p-3'>✅ No Configuration Drift Detected.</div>")
        else:
            final_html.append("<div class='card-body p-0'><pre style='background:#222; color:#fff; padding:15px; margin:0;'>")
            for line in diff:
                c = "#ccc"
                if line.startswith('+'): c = "#50fa7b"
                elif line.startswith('-'): c = "#ff5555"
                elif line.startswith('^'): c = "#f1fa8c"
                final_html.append(f"<span style='color:{c}'>{line}</span>")
            final_html.append("</pre></div>")
        
        final_html.append("</div>")

    return jsonify({"diff": "\n".join(final_html)})

@app.route('/compare_files', methods=['POST'])
def compare_files():
    file_a = request.json.get('file_a')
    file_b = request.json.get('file_b')
    
    path_a = os.path.join(config.REPORT_DIR, file_a)
    path_b = os.path.join(config.REPORT_DIR, file_b)
    
    if not os.path.exists(path_a) or not os.path.exists(path_b): return jsonify({"diff": "Error: Files missing"})
        
    with open(path_a, 'r') as f: raw_a = f.read()
    with open(path_b, 'r') as f: raw_b = f.read()
    
    id_a = extract_identity(raw_a)
    id_b = extract_identity(raw_b)
    
    final_html = []
    # Build Section 1 with Source Hints
    final_html.append(generate_identity_table(file_a, id_a, file_b, id_b))
    
    norm_a = normalize_for_diff(raw_a)
    norm_b = normalize_for_diff(raw_b)
    diff = list(difflib.unified_diff(norm_a, norm_b, fromfile=file_a, tofile=file_b, lineterm=''))
    
    final_html.append("<div class='card mb-3 shadow-sm border-dark'>")
    final_html.append("<div class='card-header bg-dark text-white fw-bold'>🔸 Section 2: Configuration Drift</div>")
    
    if not diff:
        final_html.append("<div class='card-body bg-light text-success p-3'>✅ Files are Configuration-Identical.</div>")
    else:
        final_html.append("<div class='card-body p-0'><pre style='background:#222; color:#fff; padding:15px; margin:0;'>")
        for line in diff:
            c = "#ccc"
            if line.startswith('+'): c = "#50fa7b"
            elif line.startswith('-'): c = "#ff5555"
            elif line.startswith('^'): c = "#f1fa8c"
            final_html.append(f"<span style='color:{c}'>{line}</span>")
        final_html.append("</pre></div>")
    final_html.append("</div>")
    
    return jsonify({"diff": "\n".join(final_html)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
