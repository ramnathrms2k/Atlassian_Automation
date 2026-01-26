import subprocess
import logging
from datetime import datetime
from flask import Flask, render_template, jsonify
from config import (
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

# Initialize the Flask app
app = Flask(__name__)

# ========================================================================
# SSH Functions
# ========================================================================

def execute_ssh_command(hostname, command):
    """Execute a command on a remote server via SSH."""
    try:
        ssh_cmd = [
            'ssh',
            '-o', f'ConnectTimeout={SSH_TIMEOUT}',
            '-o', 'StrictHostKeyChecking=no',
            f'{SSH_USER}@{hostname}',
            command
        ]
        
        logger.info(f"Executing SSH command on {hostname}: {command[:100]}...")
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=SSH_TIMEOUT + 5
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
    hostname = server["hostname"]
    log_path = server["log_path"]
    
    # Get today's log file name
    today_log = datetime.now().strftime(ACCESS_LOG_FORMAT)
    log_file = f"{log_path}/{today_log}"
    
    logger.info(f"Analyzing response times for {server['name']} from {log_file}")
    
    # Build the awk command to analyze slow requests
    # Field $3 = User ID, $4 = Timestamp, $10 = Time taken (ms)
    # Note: Command uses cd to log_path and references today_log file
    awk_command = (
        f"cd {log_path} && "
        f"tail -n {TAIL_LINES} {today_log} 2>/dev/null | "
        f"awk '$10 > {THRESHOLD_MS} {{ "
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
    start_time = datetime.now()
    
    results = {
        "servers": [],
        "last_update": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "config": {
            "threshold_ms": THRESHOLD_MS,
            "tail_lines": TAIL_LINES,
            "log_format": ACCESS_LOG_FORMAT
        }
    }
    
    for server in JIRA_SERVERS:
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
    config = {
        "threshold_ms": THRESHOLD_MS,
        "tail_lines": TAIL_LINES,
        "log_format": ACCESS_LOG_FORMAT
    }
    return render_template('index.html', config=config, refresh_interval=REFRESH_INTERVAL)

@app.route('/api/stats')
def api_stats():
    """JSON API endpoint for response time statistics."""
    results = get_all_response_time_stats()
    return jsonify(results)

@app.route('/refresh')
def refresh():
    """Manual refresh endpoint."""
    results = get_all_response_time_stats()
    config = {
        "threshold_ms": THRESHOLD_MS,
        "tail_lines": TAIL_LINES,
        "log_format": ACCESS_LOG_FORMAT
    }
    return render_template('index.html', results=results, config=config, refresh_interval=REFRESH_INTERVAL)

if __name__ == '__main__':
    # Runs the app. 'debug=True' reloads the app on code changes.
    # 'host=0.0.0.0' makes it accessible on your network, not just localhost.
    app.run(debug=True, host='0.0.0.0', port=5002)
