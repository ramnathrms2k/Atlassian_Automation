#!/usr/bin/env python3
"""
Multi-Server Script Executor
Web interface to execute scripts on multiple servers via SSH
"""

import sys
import os

# Add framework directory to path
framework_dir = os.path.dirname(os.path.abspath(__file__))
if framework_dir not in sys.path:
    sys.path.insert(0, framework_dir)

from flask import Flask, Blueprint, render_template_string, jsonify, request
import subprocess
import threading
import time
import re
from datetime import datetime

# Use absolute path for template_folder
framework_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(framework_dir, 'templates')
app = Blueprint('script_executor', __name__, template_folder=template_dir, static_folder='static')

# ===== CONFIGURATION =====
# Note: This will be overridden by instance configuration from instances_config.py
# These are default/example values
SERVERS = [
    {'name': 'Jira Node 1', 'host': 'jira-server-1.example.com', 'user': 'svcjira'},
    {'name': 'Jira Node 2', 'host': 'jira-server-2.example.com', 'user': 'svcjira'},
    {'name': 'Jira Node 3', 'host': 'jira-server-3.example.com', 'user': 'svcjira'},
]

SCRIPT_DIR = '/export/scripts/'  # Directory containing the script
SCRIPT_NAME = 'monitor_jira_v22.sh'  # Script filename
SCRIPT_TIMEOUT = 20  # seconds

# ===== THRESHOLD CONFIGURATION =====
THRESHOLDS = {
    # DB Server Load Average (1min, 5min, 15min)
    'db_load_warning': 10.0,      # Yellow highlight if any load > this
    'db_load_critical': 15.0,     # Red highlight if any load > this
    
    # App Server Load Average
    'app_load_warning': 5.0,
    'app_load_critical': 8.0,
    
    # Memory Usage (percentage)
    'memory_warning': 80.0,       # Yellow if memory used > 80%
    'memory_critical': 90.0,      # Red if memory used > 90%
    
    # Swap Usage (percentage)
    'swap_warning': 50.0,         # Yellow if swap used > 50%
    'swap_critical': 75.0,        # Red if swap used > 75%
    
    # Response Time (milliseconds)
    'response_time_warning': 1000,  # Yellow if avg > 1s
    'response_time_critical': 5000, # Red if avg > 5s
    
    # 95th Percentile Response Time
    'p95_warning': 2000,          # Yellow if 95th percentile > 2s
    'p95_critical': 5000,         # Red if 95th percentile > 5s
    
    # Apdex Score
    'apdex_warning': 0.95,        # Yellow if apdex < 0.95
    'apdex_critical': 0.90,       # Red if apdex < 0.90
    
    # Time Bucket Percentages
    'frustrated_warning': 1.0,    # Yellow if frustrated requests > 1%
    'frustrated_critical': 5.0,   # Red if frustrated requests > 5%
    
    # Individual User Request Time (milliseconds)
    'user_request_warning': 10000,  # Yellow if user request > 10s
    'user_request_critical': 30000, # Red if user request > 30s
}
# =========================

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Multi-Server Script Executor</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: Arial, sans-serif;
            width: 100%;
            margin: 0;
            padding: 15px;
            background-color: #f5f5f5;
        }
        .home-link {
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            background-color: #007bff;
            color: white;
            padding: 10px 20px;
            border-radius: 5px;
            text-decoration: none;
            font-weight: 500;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .home-link:hover {
            background-color: #0056b3;
            color: white;
            text-decoration: none;
        }
        h1 {
            color: #333;
            margin: 0 0 20px 0;
        }
        .controls {
            background: white;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 16px;
        }
        button:hover {
            background-color: #45a049;
        }
        button:disabled {
            background-color: #cccccc;
            cursor: not-allowed;
        }
        .status {
            margin-top: 10px;
            font-weight: bold;
        }
        .results {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 20px;
            width: 100%;
        }
        @media (max-width: 1400px) {
            .results {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        @media (max-width: 900px) {
            .results {
                grid-template-columns: 1fr;
            }
        }
        .server-result {
            background: white;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            height: 100%;
        }
        .server-header {
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            margin-left: 10px;
        }
        .status-running {
            background-color: #ffc107;
            color: #000;
        }
        .status-success {
            background-color: #4CAF50;
            color: white;
        }
        .status-error {
            background-color: #f44336;
            color: white;
        }
        .output {
            background-color: #1e1e1e;
            color: #d4d4d4;
            border: 1px solid #3e3e3e;
            border-radius: 3px;
            padding: 10px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            max-height: 600px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-wrap: break-word;
            flex: 1;
            line-height: 1.6;
        }
        /* Highlighting styles - improved contrast for dark background */
        .highlight-warning {
            background-color: #664d00;
            color: #ffc107;
            padding: 2px 4px;
            border-left: 3px solid #ffc107;
            font-weight: bold;
        }
        .highlight-critical {
            background-color: #5a1a1a;
            color: #ff6b6b;
            padding: 2px 4px;
            border-left: 3px solid #dc3545;
            font-weight: bold;
        }
        .highlight-info {
            background-color: #0c5460;
            color: #8be9fd;
            padding: 2px 4px;
            border-left: 3px solid #0c5460;
        }
        .section-header {
            font-weight: bold;
            color: #0066cc;
            margin-top: 10px;
            margin-bottom: 5px;
        }
        .timestamp {
            color: #666;
            font-size: 12px;
            margin-top: 10px;
        }
        .loading {
            text-align: center;
            padding: 20px;
            grid-column: 1 / -1;
        }
        .spinner {
            border: 4px solid #f3f3f3;
            border-top: 4px solid #3498db;
            border-radius: 50%;
            width: 40px;
            height: 40px;
            animation: spin 1s linear infinite;
            margin: 0 auto;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
    </style>
</head>
<body>
    <a href="/" class="home-link">🏠 Home</a>
    <h1>Multi-Server Script Executor</h1>
    
    <div class="controls">
        <button id="executeBtn" onclick="executeScript()">Execute Script on All Servers</button>
        <div class="status" id="status"></div>
    </div>
    
    <div class="results" id="results">
        <div class="loading">
            <div class="spinner"></div>
            <p>Click "Execute Script" to run on all servers</p>
        </div>
    </div>

    <script>
        function executeScript() {
            const btn = document.getElementById('executeBtn');
            const status = document.getElementById('status');
            const results = document.getElementById('results');
            
            btn.disabled = true;
            status.textContent = 'Executing script on all servers...';
            status.style.color = '#ffc107';
            
            // Show loading state
            results.innerHTML = `
                <div class="server-result">
                    <div class="server-header">Initializing...</div>
                    <div class="output">Connecting to servers...</div>
                </div>
            `;
            
            fetch('/execute', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                displayResults(data);
                btn.disabled = false;
                if (data.error) {
                    status.textContent = 'Error: ' + data.error;
                    status.style.color = '#f44336';
                } else {
                    status.textContent = 'Execution completed at ' + new Date().toLocaleString();
                    status.style.color = '#4CAF50';
                }
            })
            .catch(error => {
                console.error('Error:', error);
                status.textContent = 'Error: ' + error.message;
                status.style.color = '#f44336';
                btn.disabled = false;
            });
        }
        
        function displayResults(data) {
            const results = document.getElementById('results');
            
            if (data.error) {
                results.innerHTML = `
                    <div class="server-result">
                        <div class="server-header">Error</div>
                        <div class="output" style="color: #f44336;">${data.error}</div>
                    </div>
                `;
                return;
            }
            
            let html = '';
            data.results.forEach(result => {
                const statusClass = result.status === 'success' ? 'status-success' : 
                                   result.status === 'error' ? 'status-error' : 'status-running';
                const statusText = result.status === 'success' ? 'SUCCESS' : 
                                  result.status === 'error' ? 'ERROR' : 'RUNNING';
                
                html += `
                    <div class="server-result">
                        <div class="server-header">
                            ${result.server_name}
                            <span class="status-badge ${statusClass}">${statusText}</span>
                        </div>
                        <div class="output">${result.highlighted_output}</div>
                        <div class="timestamp">Executed at: ${result.timestamp}</div>
                        ${result.error ? `<div style="color: #f44336; margin-top: 10px;">Error: ${escapeHtml(result.error)}</div>` : ''}
                    </div>
                `;
            });
            
            results.innerHTML = html;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
    </script>
</body>
</html>
"""

def highlight_output(text, thresholds):
    """Apply threshold-based highlighting to output text."""
    if not text:
        return text
    
    lines = text.split('\n')
    highlighted_lines = []
    
    for line in lines:
        original_line = line
        highlighted_line = escape_html(line)
        
        # Highlight section headers
        if line.strip().startswith('---') and line.strip().endswith('---'):
            highlighted_line = f'<div class="section-header">{highlighted_line}</div>'
        
        # Check DB Server Load Average
        if 'DB Server Load and Memory' in line:
            # Look ahead for load average line
            idx = lines.index(line)
            if idx + 1 < len(lines):
                next_line = lines[idx + 1]
                load_match = re.search(r'(\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)', next_line)
                if load_match:
                    loads = [float(load_match.group(1)), float(load_match.group(2)), float(load_match.group(3))]
                    max_load = max(loads)
                    if max_load >= thresholds['db_load_critical']:
                        highlighted_line = f'<span class="highlight-critical">{highlighted_line}</span>'
                    elif max_load >= thresholds['db_load_warning']:
                        highlighted_line = f'<span class="highlight-warning">{highlighted_line}</span>'
        
        # Check App Server Load Average
        if 'App Server Load and Memory' in line:
            idx = lines.index(line)
            if idx + 1 < len(lines):
                next_line = lines[idx + 1]
                load_match = re.search(r'(\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)', next_line)
                if load_match:
                    loads = [float(load_match.group(1)), float(load_match.group(2)), float(load_match.group(3))]
                    max_load = max(loads)
                    if max_load >= thresholds['app_load_critical']:
                        highlighted_line = f'<span class="highlight-critical">{highlighted_line}</span>'
                    elif max_load >= thresholds['app_load_warning']:
                        highlighted_line = f'<span class="highlight-warning">{highlighted_line}</span>'
        
        # Check load average values themselves
        load_match = re.search(r'(\d+\.\d+),\s*(\d+\.\d+),\s*(\d+\.\d+)', line)
        if load_match:
            loads = [float(load_match.group(1)), float(load_match.group(2)), float(load_match.group(3))]
            max_load = max(loads)
            # Check if this is DB or App load based on context
            context_line = lines[max(0, lines.index(line) - 2):lines.index(line)]
            is_db = any('DB Server' in l for l in context_line)
            is_app = any('App Server' in l for l in context_line)
            
            if is_db:
                if max_load >= thresholds['db_load_critical']:
                    highlighted_line = re.sub(
                        r'(\d+\.\d+,\s*\d+\.\d+,\s*\d+\.\d+)',
                        r'<span class="highlight-critical">\1</span>',
                        highlighted_line
                    )
                elif max_load >= thresholds['db_load_warning']:
                    highlighted_line = re.sub(
                        r'(\d+\.\d+,\s*\d+\.\d+,\s*\d+\.\d+)',
                        r'<span class="highlight-warning">\1</span>',
                        highlighted_line
                    )
            elif is_app:
                if max_load >= thresholds['app_load_critical']:
                    highlighted_line = re.sub(
                        r'(\d+\.\d+,\s*\d+\.\d+,\s*\d+\.\d+)',
                        r'<span class="highlight-critical">\1</span>',
                        highlighted_line
                    )
                elif max_load >= thresholds['app_load_warning']:
                    highlighted_line = re.sub(
                        r'(\d+\.\d+,\s*\d+\.\d+,\s*\d+\.\d+)',
                        r'<span class="highlight-warning">\1</span>',
                        highlighted_line
                    )
        
        # Check Average Response Time
        response_match = re.search(r'Average Response Time:\s*(\d+\.?\d*)\s*ms', line)
        if response_match:
            response_time = float(response_match.group(1))
            if response_time >= thresholds['response_time_critical']:
                highlighted_line = re.sub(
                    r'Average Response Time:\s*(\d+\.?\d*)\s*ms',
                    r'Average Response Time: <span class="highlight-critical">\1 ms</span>',
                    highlighted_line
                )
            elif response_time >= thresholds['response_time_warning']:
                highlighted_line = re.sub(
                    r'Average Response Time:\s*(\d+\.?\d*)\s*ms',
                    r'Average Response Time: <span class="highlight-warning">\1 ms</span>',
                    highlighted_line
                )
        
        # Check 95th Percentile
        p95_match = re.search(r'95th Percentile:\s*(\d+)\s*ms', line)
        if p95_match:
            p95 = int(p95_match.group(1))
            if p95 >= thresholds['p95_critical']:
                highlighted_line = re.sub(
                    r'95th Percentile:\s*(\d+)\s*ms',
                    r'95th Percentile: <span class="highlight-critical">\1 ms</span>',
                    highlighted_line
                )
            elif p95 >= thresholds['p95_warning']:
                highlighted_line = re.sub(
                    r'95th Percentile:\s*(\d+)\s*ms',
                    r'95th Percentile: <span class="highlight-warning">\1 ms</span>',
                    highlighted_line
                )
        
        # Check Apdex Score
        apdex_match = re.search(r'Apdex Score:\s*(\d+\.\d+)', line)
        if apdex_match:
            apdex = float(apdex_match.group(1))
            if apdex < thresholds['apdex_critical']:
                highlighted_line = re.sub(
                    r'Apdex Score:\s*(\d+\.\d+)',
                    r'Apdex Score: <span class="highlight-critical">\1</span>',
                    highlighted_line
                )
            elif apdex < thresholds['apdex_warning']:
                highlighted_line = re.sub(
                    r'Apdex Score:\s*(\d+\.\d+)',
                    r'Apdex Score: <span class="highlight-warning">\1</span>',
                    highlighted_line
                )
        
        # Check Frustrated requests in time buckets
        frustrated_match = re.search(r'(\d+\.\d+)%\s*\(Frustrated\)', line)
        if frustrated_match:
            pct = float(frustrated_match.group(1))
            if pct >= thresholds['frustrated_critical']:
                highlighted_line = re.sub(
                    r'(\d+\.\d+)%\s*\(Frustrated\)',
                    r'<span class="highlight-critical">\1% (Frustrated)</span>',
                    highlighted_line
                )
            elif pct >= thresholds['frustrated_warning']:
                highlighted_line = re.sub(
                    r'(\d+\.\d+)%\s*\(Frustrated\)',
                    r'<span class="highlight-warning">\1% (Frustrated)</span>',
                    highlighted_line
                )
        
        # Check individual user request times
        user_request_match = re.search(r'\|(\d+)\s*\|.*\|(\d+)\s*\|', line)
        if user_request_match and 'UserID' not in line:
            max_time = int(user_request_match.group(2))
            if max_time >= thresholds['user_request_critical']:
                highlighted_line = f'<span class="highlight-critical">{highlighted_line}</span>'
            elif max_time >= thresholds['user_request_warning']:
                highlighted_line = f'<span class="highlight-warning">{highlighted_line}</span>'
        
        highlighted_lines.append(highlighted_line)
    
    return '\n'.join(highlighted_lines)

def escape_html(text):
    """Escape HTML special characters."""
    if not text:
        return ''
    return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&#x27;'))

def execute_script_on_server(server_info):
    """Execute script on a single server via SSH."""
    result = {
        'server_name': server_info['name'],
        'host': server_info['host'],
        'status': 'running',
        'output': '',
        'highlighted_output': '',
        'error': None,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # Build SSH command: cd to directory, then execute ./script.sh
        ssh_cmd = [
            'ssh',
            '-o', 'StrictHostKeyChecking=no',
            '-o', 'ConnectTimeout=5',
            f"{server_info['user']}@{server_info['host']}",
            f"cd {SCRIPT_DIR} && ./{SCRIPT_NAME}"
        ]
        
        # Execute command
        process = subprocess.Popen(
            ssh_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for completion with timeout
        try:
            stdout, stderr = process.communicate(timeout=SCRIPT_TIMEOUT)
            return_code = process.returncode
            
            if return_code == 0:
                result['status'] = 'success'
                result['output'] = stdout
                result['highlighted_output'] = highlight_output(stdout, THRESHOLDS)
            else:
                result['status'] = 'error'
                result['output'] = stdout
                result['highlighted_output'] = highlight_output(stdout, THRESHOLDS)
                result['error'] = stderr if stderr else f'Script exited with code {return_code}'
        
        except subprocess.TimeoutExpired:
            process.kill()
            result['status'] = 'error'
            result['error'] = f'Script execution timed out after {SCRIPT_TIMEOUT} seconds'
            result['output'] = 'Execution was terminated due to timeout'
            result['highlighted_output'] = escape_html(result['output'])
        
    except Exception as e:
        result['status'] = 'error'
        result['error'] = str(e)
        result['output'] = f'Failed to execute script: {str(e)}'
        result['highlighted_output'] = escape_html(result['output'])
    
    return result

@app.route('/')
def index():
    """Main page."""
    # Inject url_for into the template so JavaScript can use it
    from flask import url_for
    # Replace the hardcoded /execute path with the correct Flask URL
    template_with_url = HTML_TEMPLATE.replace(
        "fetch('/execute', {",
        f"fetch('{url_for('script_executor.execute')}', {{"
    )
    return render_template_string(template_with_url)

@app.route('/execute', methods=['POST'])
def execute():
    """Execute script on all servers."""
    try:
        results = []
        threads = []
        results_lock = threading.Lock()
        
        def run_script(server_info):
            result = execute_script_on_server(server_info)
            with results_lock:
                results.append(result)
        
        # Start threads for parallel execution
        for server in SERVERS:
            thread = threading.Thread(target=run_script, args=(server,))
            thread.start()
            threads.append(thread)
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Sort results by server name for consistent display
        results.sort(key=lambda x: x['server_name'])
        
        return jsonify({
            'status': 'completed',
            'results': results,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
    
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }), 500

@app.route('/health', methods=['GET'])
def health():
    """Health check."""
    return jsonify({
        'status': 'healthy',
        'servers_configured': len(SERVERS),
        'script_dir': SCRIPT_DIR,
        'script_name': SCRIPT_NAME,
        'thresholds': THRESHOLDS,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    })

if __name__ == '__main__':
    print(f"Starting Multi-Server Script Executor")
    print(f"Configured servers: {len(SERVERS)}")
    for server in SERVERS:
        print(f"  - {server['name']}: {server['user']}@{server['host']}")
    print(f"Script directory: {SCRIPT_DIR}")
    print(f"Script name: {SCRIPT_NAME}")
    print(f"Execution command: cd {SCRIPT_DIR} && ./{SCRIPT_NAME}")
    print(f"\nThreshold Configuration:")
    for key, value in THRESHOLDS.items():
        print(f"  - {key}: {value}")
    print(f"\nAccess the web interface at: http://0.0.0.0:5000")
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
