import sys
import os
import importlib.util

# Add framework directory to path so we can import config
framework_dir = os.path.dirname(os.path.abspath(__file__))
if framework_dir not in sys.path:
    sys.path.insert(0, framework_dir)

# Load config with unique name to avoid conflicts
config_path = os.path.join(framework_dir, 'config.py')
spec = importlib.util.spec_from_file_location("preflight_validator_config", config_path)
preflight_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preflight_config)

# Register with unique name to avoid conflicts with other frameworks
# Don't overwrite sys.modules['config'] - use a framework-specific name
sys.modules['preflight_validator_config'] = preflight_config

import subprocess
import re
import difflib
import datetime
from flask import Flask, Blueprint, render_template, jsonify, request
import preflight_validator_config as config

# Use absolute path for template_folder
framework_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(framework_dir, 'templates')
app = Blueprint('preflight_validator', __name__, template_folder=template_dir, static_folder='static')

# Ensure reports directory exists
if not os.path.exists(config.REPORT_DIR):
    os.makedirs(config.REPORT_DIR)

def ansi_to_html(text):
    """Converts ANSI colors to HTML with improved readability and syntax highlighting"""
    import re
    
    # Step 1: Remove or replace the "4" indentation character with proper spacing FIRST
    text = re.sub(r'^(\s*)4\s+', r'\1    ', text, flags=re.MULTILINE)
    
    # Step 2: Use unique markers that won't be matched by regex patterns
    # Use markers with special characters that regex won't match
    MARKER_CUSTOM_START = '\x01CUSTOM\x01'
    MARKER_CUSTOM_END = '\x02CUSTOM\x02'
    MARKER_KEYWORD_START = '\x01KEYWORD\x01'
    MARKER_KEYWORD_END = '\x02KEYWORD\x02'
    MARKER_STRING_START = '\x01STRING\x01'
    MARKER_STRING_END = '\x02STRING\x02'
    MARKER_VAR_START = '\x01VAR\x01'
    MARKER_VAR_END = '\x02VAR\x02'
    MARKER_OP_START = '\x01OP\x01'
    MARKER_OP_END = '\x02OP\x02'
    MARKER_PATH_START = '\x01PATH\x01'
    MARKER_PATH_END = '\x02PATH\x02'
    MARKER_JVM_START = '\x01JVM\x01'
    MARKER_JVM_END = '\x02JVM\x02'
    
    # Step 3: Apply syntax highlighting to RAW text (before ANSI conversion)
    lines = text.split('\n')
    highlighted_lines = []
    
    for line in lines:
        # 1. Highlight [CUSTOM] markers first
        line = re.sub(r'(\[CUSTOM\])', f'{MARKER_CUSTOM_START}\\1{MARKER_CUSTOM_END}', line)
        
        # 2. Highlight export keyword
        line = re.sub(r'\b(export)\s+', f'{MARKER_KEYWORD_START}\\1{MARKER_KEYWORD_END} ', line)
        
        # 3. Highlight quoted strings (do this before paths to avoid conflicts)
        line = re.sub(r'("([^"]*)")', f'{MARKER_STRING_START}\\1{MARKER_STRING_END}', line)
        line = re.sub(r"('([^']*)')", f"{MARKER_STRING_START}\\1{MARKER_STRING_END}", line)
        
        # 4. Highlight variable names (VAR_NAME=) - but not if inside a string
        def highlight_var(match):
            var_name = match.group(1)
            pos = match.start()
            before = line[:pos]
            # Check if inside a string marker
            open_strings = before.count(MARKER_STRING_START)
            close_strings = before.count(MARKER_STRING_END)
            if open_strings > close_strings:
                return match.group(0)  # Inside string, don't highlight
            return f'{MARKER_VAR_START}{var_name}{MARKER_VAR_END}{MARKER_OP_START}={MARKER_OP_END}'
        
        line = re.sub(r'\b([A-Z_][A-Z0-9_]+)(=)', highlight_var, line)
        
        # 5. Highlight paths - but not if inside strings
        def highlight_path(match):
            path = match.group(1)
            pos = match.start()
            before = line[:pos]
            # Check if inside a string marker
            open_strings = before.count(MARKER_STRING_START)
            close_strings = before.count(MARKER_STRING_END)
            if open_strings > close_strings:
                return path  # Inside string, don't highlight
            # Check if already inside a path marker (avoid double highlighting)
            if MARKER_PATH_START in before and MARKER_PATH_END not in before[pos:]:
                return path  # Already inside a path marker
            return f'{MARKER_PATH_START}{path}{MARKER_PATH_END}'
        
        # Match full paths (greedy match, stop at whitespace, quotes, =, or end of line)
        line = re.sub(r'(?<!["\'])(/[^\s"\'=\n\x01\x02]+)(?![^\x01\x02]*[\x01\x02])', highlight_path, line)
        
        # 6. Highlight JVM flags - but not if inside strings
        def highlight_jvm_flag(match):
            flag = match.group(1)
            pos = match.start()
            before = line[:pos]
            open_strings = before.count(MARKER_STRING_START)
            close_strings = before.count(MARKER_STRING_END)
            if open_strings > close_strings:
                return flag  # Inside string, don't highlight
            return f'{MARKER_JVM_START}{flag}{MARKER_JVM_END}'
        
        line = re.sub(r'\b(-[XD][a-zA-Z0-9_.-]+)', highlight_jvm_flag, line)
        line = re.sub(r'\b(-XX:[+-][a-zA-Z0-9_.=]+)', highlight_jvm_flag, line)
        
        highlighted_lines.append(line)
    
    text = '\n'.join(highlighted_lines)
    
    # Step 4: Convert markers to HTML spans
    text = text.replace(MARKER_CUSTOM_START, '<span class="custom-marker">')
    text = text.replace(MARKER_CUSTOM_END, '</span>')
    text = text.replace(MARKER_KEYWORD_START, '<span class="keyword">')
    text = text.replace(MARKER_KEYWORD_END, '</span>')
    text = text.replace(MARKER_STRING_START, '<span class="string">')
    text = text.replace(MARKER_STRING_END, '</span>')
    text = text.replace(MARKER_VAR_START, '<span class="var-name">')
    text = text.replace(MARKER_VAR_END, '</span>')
    text = text.replace(MARKER_OP_START, '<span class="operator">')
    text = text.replace(MARKER_OP_END, '</span>')
    text = text.replace(MARKER_PATH_START, '<span class="path">')
    text = text.replace(MARKER_PATH_END, '</span>')
    text = text.replace(MARKER_JVM_START, '<span class="jvm-flag">')
    text = text.replace(MARKER_JVM_END, '</span>')
    
    # Step 5: Convert ANSI codes to HTML (after syntax highlighting)
    COLOR_MAP = {
        # Red - use brighter red for better visibility on dark background
        '\x1b[31m': '<span class="ansi-red">', 
        # Green - use brighter green for better visibility
        '\x1b[32m': '<span class="ansi-green">', 
        # Yellow - use brighter yellow for better visibility
        '\x1b[33m': '<span class="ansi-yellow">', 
        # Blue - use brighter blue for better visibility
        '\x1b[34m': '<span class="ansi-blue">', 
        # Magenta - use brighter magenta for better visibility
        '\x1b[35m': '<span class="ansi-magenta">', 
        # Cyan - use brighter cyan for better visibility
        '\x1b[36m': '<span class="ansi-cyan">', 
        # Bold
        '\x1b[1m':  '<span class="ansi-bold">', 
        # Reset
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
    # Use explicit template path to ensure correct template is loaded
    template_path = os.path.join(framework_dir, 'templates', 'index.html')
    
    # Read the template file directly to ensure we get the correct one
    import jinja2
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Create a template environment with the blueprint's template folder
    template_loader = jinja2.FileSystemLoader(template_dir)
    template_env = jinja2.Environment(loader=template_loader)
    
    # Make url_for available in template
    from flask import current_app, url_for
    def url_for_helper(endpoint, **values):
        return current_app.url_for(endpoint, **values)
    template_env.globals['url_for'] = url_for_helper
    
    template = template_env.from_string(template_content)
    
    return template.render(nodes=config.HOSTS)

@app.route('/validate', methods=['POST'])
def validate_node():
    host = request.json.get('host')
    if host not in config.HOSTS: return jsonify({"output": "Unauthorized"}), 400

    # Get the full path to the validator script (in the same directory as app.py)
    validator_script_path = os.path.join(framework_dir, config.VALIDATOR_SCRIPT)
    
    # Check if the script exists
    if not os.path.exists(validator_script_path):
        return jsonify({"output": f"Error: Validator script not found at {validator_script_path}"}), 500
    
    # Copy the validator script to the remote server
    scp_result = subprocess.run(
        ["scp", "-o", "StrictHostKeyChecking=no", "-q", validator_script_path, f"{config.SSH_USER}@{host}:/tmp/nv.py"],
        capture_output=True,
        text=True
    )
    
    # Check if scp was successful
    if scp_result.returncode != 0:
        return jsonify({
            "output": f"Error copying validator script to {host}: {scp_result.stderr}"
        }), 500

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
