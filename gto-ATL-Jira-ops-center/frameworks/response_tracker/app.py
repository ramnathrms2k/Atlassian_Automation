import sys
import os
import importlib.util

# Define framework_dir once at the top
framework_dir = os.path.dirname(os.path.abspath(__file__))
if framework_dir not in sys.path:
    sys.path.insert(0, framework_dir)

# Load config with unique name to avoid conflicts
# Config will be injected later when instance is selected
config_path = os.path.join(framework_dir, 'config.py')
spec = importlib.util.spec_from_file_location("response_tracker_config", config_path)
response_config = importlib.util.module_from_spec(spec)

# Add parent directory for config_manager import
parent_dir = os.path.dirname(os.path.dirname(framework_dir))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

spec.loader.exec_module(response_config)

# Register with unique name to avoid conflicts with other frameworks
# Don't overwrite sys.modules['config'] - use a framework-specific name
sys.modules['response_tracker_config'] = response_config

import subprocess
import logging
from datetime import datetime
from flask import Flask, Blueprint, render_template, jsonify, url_for

# Import from the framework-specific config module
import response_tracker_config
from response_tracker_config import (
    JIRA_SERVERS, SSH_USER, SSH_TIMEOUT,
    ACCESS_LOG_FORMAT, TAIL_LINES, THRESHOLD_MS, REFRESH_INTERVAL
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jira_response_time_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize the Flask app as Blueprint
# Use absolute path for template_folder (framework_dir already defined above)
template_dir = os.path.join(framework_dir, 'templates')
app = Blueprint('response_tracker', __name__, template_folder=template_dir, static_folder='static')

# Before each request, ensure config is loaded from injected config
@app.before_request
def load_config_before_request():
    """Load config from injected config before each request."""
    try:
        # Try to get injected config
        parent_dir = os.path.dirname(os.path.dirname(framework_dir))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        
        from config_manager import get_injected_config
        injected_config = get_injected_config('response-tracker')
        
        if injected_config:
            # Inject config into the framework-specific config module
            import response_tracker_config as config
            if hasattr(config, 'inject_config'):
                config.inject_config(injected_config)
            
            # Update the module-level variables by re-reading from config module
            global JIRA_SERVERS, SSH_USER, SSH_TIMEOUT, ACCESS_LOG_FORMAT, TAIL_LINES, THRESHOLD_MS, REFRESH_INTERVAL
            JIRA_SERVERS = config.JIRA_SERVERS
            SSH_USER = config.SSH_USER
            SSH_TIMEOUT = config.SSH_TIMEOUT
            ACCESS_LOG_FORMAT = config.ACCESS_LOG_FORMAT
            TAIL_LINES = config.TAIL_LINES
            THRESHOLD_MS = config.THRESHOLD_MS
            REFRESH_INTERVAL = config.REFRESH_INTERVAL
    except Exception as e:
        # If config injection fails, use defaults (already loaded)
        logger.warning(f"Could not load injected config: {e}")
        pass

# ========================================================================
# SSH Functions
# ========================================================================

def execute_ssh_command(hostname, command):
    """Execute a command on a remote server via SSH."""
    # Re-read config to ensure we have latest values
    import response_tracker_config as config
    current_ssh_user = config.SSH_USER
    current_ssh_timeout = config.SSH_TIMEOUT
    
    try:
        ssh_cmd = [
            'ssh',
            '-o', f'ConnectTimeout={current_ssh_timeout}',
            '-o', 'StrictHostKeyChecking=no',
            f'{current_ssh_user}@{hostname}',
            command
        ]
        
        logger.info(f"Executing SSH command on {hostname}: {command[:100]}...")
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=current_ssh_timeout + 5
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            logger.debug(f"SSH command succeeded on {hostname}")
            return {"success": True, "output": output, "error": None}
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.warning(f"SSH command failed on {hostname} (code {result.returncode}): {error_msg[:200]}")
            return {"success": False, "output": None, "error": error_msg}
    except subprocess.TimeoutExpired:
        logger.error(f"SSH timeout on {hostname}")
        return {"success": False, "output": None, "error": "SSH Timeout"}
    except Exception as e:
        logger.error(f"SSH error on {hostname}: {str(e)}", exc_info=True)
        return {"success": False, "output": None, "error": str(e)}

# ========================================================================
# Response Time Analysis Functions
# ========================================================================

def get_response_time_stats(server):
    """Get response time statistics from a Jira server's access log."""
    # Re-read config to ensure we have latest values
    import response_tracker_config as config
    current_access_log_format = config.ACCESS_LOG_FORMAT
    current_tail_lines = config.TAIL_LINES
    current_threshold_ms = config.THRESHOLD_MS
    
    hostname = server["hostname"]
    log_path = server["log_path"]
    
    # Get today's log file name
    today_log = datetime.now().strftime(current_access_log_format)
    log_file = f"{log_path}/{today_log}"
    
    logger.info(f"Analyzing response times for {server['name']} from {log_file}")
    
    # Build the awk command to analyze slow requests
    # Field $3 = User ID, $4 = Timestamp, $10 = Time taken (ms)
    # Note: Command uses cd to log_path and references today_log file
    awk_command = (
        f"cd {log_path} && "
        f"tail -n {current_tail_lines} {today_log} 2>/dev/null | "
        f"awk '$10 > {current_threshold_ms} {{ "
        f"count[$3]++; "
        f"if (max_time[$3] < $10) {{ max_time[$3] = $10; }} "
        f"last_timestamp[$3] = $4; "
        f"last_time_taken[$3] = $10; "
        f"}} "
        f"END {{ "
        f"for (key in count) {{ "
        f"  sub(/\\[/, \"\", last_timestamp[key]); "
        f"  printf \"%s\\t%s\\t%s\\t%s\\t%s\\n\", "
        f"    count[key], max_time[key], last_time_taken[key], "
        f"    last_timestamp[key], key; "
        f"}} "
        f"}}' | sort -nr"
    )
    
    # Execute the command
    result = execute_ssh_command(hostname, awk_command)
    
    if not result["success"]:
        return {
            "server_name": server["name"],
            "hostname": hostname,
            "status": "Error",
            "error": result["error"],
            "data": []
        }
    
    # Parse the output
    data = []
    if result["output"]:
        lines = result["output"].strip().split('\n')
        # Skip header line if present
        for line in lines:
            if line.strip() and not line.startswith("Count"):
                parts = line.split('\t')
                if len(parts) >= 5:
                    try:
                        data.append({
                            "count": int(parts[0]),
                            "max_time_taken": int(parts[1]),
                            "last_time_taken": int(parts[2]),
                            "last_timestamp": parts[3],
                            "user_id": parts[4]
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"Failed to parse line for {server['name']}: {line[:100]}, error: {e}")
                        continue
    
    return {
        "server_name": server["name"],
        "hostname": hostname,
        "status": "Online",
        "error": None,
        "data": data,
        "total_records": len(data)
    }

def get_all_response_time_stats():
    """Get response time statistics from all Jira servers."""
    logger.info("Starting response time analysis for all servers")
    
    # Re-read config values from config module to ensure we have latest
    import response_tracker_config as config
    current_servers = config.JIRA_SERVERS
    current_ssh_user = config.SSH_USER
    current_threshold = config.THRESHOLD_MS
    current_tail_lines = config.TAIL_LINES
    
    logger.info(f"Using {len(current_servers)} servers, SSH user: {current_ssh_user}, threshold: {current_threshold}ms")
    
    start_time = datetime.now()
    
    results = {
        "servers": [],
        "last_update": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "threshold_ms": current_threshold,
            "tail_lines": current_tail_lines,
            "log_format": config.ACCESS_LOG_FORMAT
        }
    }
    
    for server in current_servers:
        stats = get_response_time_stats(server)
        results["servers"].append(stats)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Response time analysis completed in {elapsed:.2f} seconds")
    
    return results

# ========================================================================
# Flask Routes
# ========================================================================

@app.route('/')
def index():
    """Renders the main page."""
    logger.info("Response Tracker index route called")
    # Re-read config to ensure we have latest values
    import response_tracker_config as config
    current_threshold = config.THRESHOLD_MS
    current_tail_lines = config.TAIL_LINES
    current_log_format = config.ACCESS_LOG_FORMAT
    current_refresh_interval = config.REFRESH_INTERVAL
    
    config_dict = {
        "threshold_ms": current_threshold,
        "tail_lines": current_tail_lines,
        "log_format": current_log_format
    }
    
    # Use explicit template path to ensure correct template is loaded
    template_path = os.path.join(framework_dir, 'templates', 'index.html')
    logger.info(f"Response Tracker rendering template from: {template_path}")
    
    # Use render_template_string with explicit file reading to ensure correct template
    from flask import current_app
    import jinja2
    
    # Read the template file directly
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Create a template environment with the blueprint's template folder
    template_loader = jinja2.FileSystemLoader(template_dir)
    template_env = jinja2.Environment(loader=template_loader)
    
    # Make url_for available in template - use current_app to get the Flask app instance
    from flask import current_app
    def url_for_helper(endpoint, **values):
        return current_app.url_for(endpoint, **values)
    template_env.globals['url_for'] = url_for_helper
    
    template = template_env.from_string(template_content)
    
    return template.render(
        config=config_dict,
        refresh_interval=current_refresh_interval
    )

@app.route('/api/stats')
def api_stats():
    """JSON API endpoint for response time statistics."""
    results = get_all_response_time_stats()
    return jsonify(results)

@app.route('/refresh')
def refresh():
    """Manual refresh endpoint."""
    # Re-read config to ensure we have latest values
    import response_tracker_config as config
    current_threshold = config.THRESHOLD_MS
    current_tail_lines = config.TAIL_LINES
    current_log_format = config.ACCESS_LOG_FORMAT
    current_refresh_interval = config.REFRESH_INTERVAL
    
    results = get_all_response_time_stats()
    config_dict = {
        "threshold_ms": current_threshold,
        "tail_lines": current_tail_lines,
        "log_format": current_log_format
    }
    
    # Use explicit template path to ensure correct template is loaded
    template_path = os.path.join(framework_dir, 'templates', 'index.html')
    
    # Read the template file directly
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Create a template environment with the blueprint's template folder
    import jinja2
    template_loader = jinja2.FileSystemLoader(template_dir)
    template_env = jinja2.Environment(loader=template_loader)
    
    # Make url_for available in template - use current_app to get the Flask app instance
    from flask import current_app
    def url_for_helper(endpoint, **values):
        return current_app.url_for(endpoint, **values)
    template_env.globals['url_for'] = url_for_helper
    
    template = template_env.from_string(template_content)
    
    return template.render(
        results=results,
        config=config_dict,
        refresh_interval=current_refresh_interval
    )

if __name__ == '__main__':
    # Runs the app. 'debug=True' reloads the app on code changes.
    # 'host=0.0.0.0' makes it accessible on your network, not just localhost.
    app.run(debug=True, host='0.0.0.0', port=5002)
