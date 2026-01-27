# app.py - Health Dashboard Framework
# Adapted for config injection

import sys
import os

# Add framework directory to path so we can import config
framework_dir = os.path.dirname(os.path.abspath(__file__))
if framework_dir not in sys.path:
    sys.path.insert(0, framework_dir)

# Add parent directory to path for config_manager access
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Use a unique module name for this framework's config to avoid conflicts
import importlib.util
config_path = os.path.join(framework_dir, 'config.py')
spec = importlib.util.spec_from_file_location("health_dashboard_config", config_path)
health_config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(health_config)

# Register with unique name to avoid conflicts with other frameworks
# Don't overwrite sys.modules['config'] - use a framework-specific name
sys.modules['health_dashboard_config'] = health_config

# Now import the rest
import requests
import datetime
import subprocess
import json
import pymysql
import logging
from flask import Flask, Blueprint, render_template, jsonify, url_for

# Import from the framework-specific config module
import health_dashboard_config
from health_dashboard_config import (
    JIRA_SERVERS, JIRA_PAT, DB_SERVER, SSH_USER, SSH_TIMEOUT,
    AUTO_REFRESH_INTERVAL, DB_CONNECTION_THRESHOLDS, SYSTEM_THRESHOLDS,
    JIRA_API_TIMEOUT, DB_CONNECT_TIMEOUT, DB_READ_TIMEOUT, DB_MAX_CONNECTIONS, DB_POOL_PER_APP_NODE
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('jira_health_dashboard.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Create Blueprint for integration with main app
# Use absolute path for template_folder
framework_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(framework_dir, 'templates')
app = Blueprint('health_dashboard', __name__, template_folder=template_dir, static_folder='static')

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
        injected_config = get_injected_config('health-dashboard')
        
        if injected_config:
            # Inject config into the config module
            import health_dashboard_config as config
            if hasattr(config, 'inject_config'):
                config.inject_config(injected_config)
            
            # Update the module-level variables by re-reading from config module
            global JIRA_SERVERS, JIRA_PAT, DB_SERVER, SSH_USER, SSH_TIMEOUT
            global AUTO_REFRESH_INTERVAL, DB_CONNECTION_THRESHOLDS, SYSTEM_THRESHOLDS
            global JIRA_API_TIMEOUT, DB_CONNECT_TIMEOUT, DB_READ_TIMEOUT, DB_MAX_CONNECTIONS, DB_POOL_PER_APP_NODE
            JIRA_SERVERS = config.JIRA_SERVERS
            JIRA_PAT = config.JIRA_PAT
            DB_SERVER = config.DB_SERVER
            SSH_USER = config.SSH_USER
            SSH_TIMEOUT = config.SSH_TIMEOUT
            AUTO_REFRESH_INTERVAL = config.AUTO_REFRESH_INTERVAL
            DB_CONNECTION_THRESHOLDS = config.DB_CONNECTION_THRESHOLDS
            SYSTEM_THRESHOLDS = config.SYSTEM_THRESHOLDS
            JIRA_API_TIMEOUT = config.JIRA_API_TIMEOUT
            DB_CONNECT_TIMEOUT = config.DB_CONNECT_TIMEOUT
            DB_READ_TIMEOUT = config.DB_READ_TIMEOUT
            DB_MAX_CONNECTIONS = config.DB_MAX_CONNECTIONS
            DB_POOL_PER_APP_NODE = config.DB_POOL_PER_APP_NODE
    except Exception as e:
        # If config injection fails, use defaults (already loaded)
        logger.warning(f"Could not load injected config: {e}")

def initialize_with_config(instance_config):
    """Initialize framework with instance configuration."""
    import config
    if hasattr(config, 'inject_config'):
        config.inject_config(instance_config)

# ========================================================================
# Jira Index Health Functions
# ========================================================================

def fetch_jira_health(server_name, base_url, pat):
    """Fetches the index summary from a single Jira server."""
    # Re-read config to ensure we have latest values
    import config
    current_timeout = config.JIRA_API_TIMEOUT
    
    api_url = f"{base_url}/rest/api/2/index/summary"
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': 'application/json'
    }
    
    start_time = datetime.datetime.now()
    
    try:
        # Set configurable timeout (Jira index summary can take time for large instances)
        response = requests.get(api_url, headers=headers, timeout=current_timeout)
        
        # Get the elapsed time from the response object for accuracy
        time_taken = response.elapsed.total_seconds()
        
        # Check for HTTP errors (e.g., 401 Unauthorized, 404 Not Found, 500 Server Error)
        response.raise_for_status()
        
        # Parse the JSON response
        data = response.json()
        index_data = data.get("issueIndex", {})
        
        # Build a report dictionary with the extracted data
        report = {
            "server_name": server_name,
            "status": "Online",
            "current_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
            "time_taken_sec": f"{time_taken:.2f}",
            "db_count": index_data.get("countInDatabase", "N/A"),
            "index_count": index_data.get("countInIndex", "N/A"),
            "archive_count": index_data.get("countInArchive", "N/A"),
            "db_updated": index_data.get("lastUpdatedInDatabase", "N/A"),
            "index_updated": index_data.get("lastUpdatedInIndex", "N/A"),
        }
        
    except requests.exceptions.HTTPError as e:
        report = _create_error_report(server_name, start_time, f"HTTP Error: {e.response.status_code}")
    except requests.exceptions.ConnectionError:
        report = _create_error_report(server_name, start_time, "Connection Error")
    except requests.exceptions.Timeout:
        report = _create_error_report(server_name, start_time, "Request Timed Out")
    except Exception as e:
        # Catch any other errors (e.g., JSON parsing)
        report = _create_error_report(server_name, start_time, f"Error: {str(e)}")
        
    return report

def _create_error_report(server_name, start_time, error_message):
    """Helper function to create a standardized error report."""
    return {
        "server_name": server_name,
        "status": f"{error_message}",
        "current_time": start_time.strftime("%Y-%m-%d %H:%M:%S"),
        "time_taken_sec": "N/A",
        "db_count": "N/A",
        "index_count": "N/A",
        "archive_count": "N/A",
        "db_updated": "N/A",
        "index_updated": "N/A",
    }

# ========================================================================
# SSH Functions
# ========================================================================

def execute_ssh_command(hostname, command):
    """Execute a command on a remote server via SSH."""
    # Re-read config to ensure we have latest values
    import config
    current_ssh_user = config.SSH_USER
    current_ssh_timeout = config.SSH_TIMEOUT
    
    try:
        # Use subprocess with list to avoid shell escaping issues
        ssh_cmd = [
            'ssh',
            '-o', f'ConnectTimeout={current_ssh_timeout}',
            '-o', 'StrictHostKeyChecking=no',
            f'{current_ssh_user}@{hostname}',
            command
        ]
        
        logger.info(f"Executing SSH command on {hostname}: {command[:50]}...")
        
        result = subprocess.run(
            ssh_cmd,
            capture_output=True,
            text=True,
            timeout=current_ssh_timeout + 5
        )
        
        if result.returncode == 0:
            output = result.stdout.strip()
            logger.debug(f"SSH command succeeded on {hostname}: {output[:100]}")
            return {"success": True, "output": output, "error": None}
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            logger.warning(f"SSH command failed on {hostname} (code {result.returncode}): {error_msg}")
            return {"success": False, "output": None, "error": error_msg}
    except subprocess.TimeoutExpired:
        logger.error(f"SSH timeout on {hostname}")
        return {"success": False, "output": None, "error": "SSH Timeout"}
    except Exception as e:
        logger.error(f"SSH error on {hostname}: {str(e)}", exc_info=True)
        return {"success": False, "output": None, "error": str(e)}

# ========================================================================
# System Metrics Functions
# ========================================================================

def get_system_metrics(hostname):
    """Collect system metrics from a remote server."""
    logger.info(f"Collecting system metrics from {hostname}")
    
    metrics = {
        "hostname": hostname,
        "status": "Online",
        "error": None,
        "cpu_percent": "N/A",
        "memory_percent": "N/A",
        "swap_percent": "N/A",
        "load_avg": "N/A",
        "disk_usage_local": "N/A",
        "disk_usage_shared_home": "N/A",  # For app nodes
        "disk_usage_binlogs": "N/A",  # For DB node
        "db_connections": "N/A"
    }
    
    try:
        # Get CPU usage - simpler approach using /proc/loadavg and vmstat or top
        # Try multiple methods for better compatibility
        cpu_cmd = "grep 'cpu ' /proc/stat | awk '{usage=($2+$4)*100/($2+$4+$5)} END {print usage}'"
        cpu_result = execute_ssh_command(hostname, cpu_cmd)
        if cpu_result["success"] and cpu_result["output"]:
            try:
                cpu_val = float(cpu_result["output"].strip())
                metrics["cpu_percent"] = round(cpu_val, 1)
                logger.debug(f"CPU for {hostname}: {metrics['cpu_percent']}%")
            except Exception as e:
                logger.warning(f"Failed to parse CPU for {hostname}: {e}, output: {cpu_result['output']}")
        
        # Get memory usage - simpler command
        mem_cmd = "free | awk '/^Mem:/ {printf \"%.1f\", ($3/$2) * 100.0}'"
        mem_result = execute_ssh_command(hostname, mem_cmd)
        if mem_result["success"] and mem_result["output"]:
            try:
                metrics["memory_percent"] = round(float(mem_result["output"].strip()), 1)
                logger.debug(f"Memory for {hostname}: {metrics['memory_percent']}%")
            except Exception as e:
                logger.warning(f"Failed to parse memory for {hostname}: {e}, output: {mem_result['output']}")
        
        # Get swap usage
        swap_cmd = "free | awk '/^Swap:/ {if ($2==0) print \"0\"; else printf \"%.1f\", ($3/$2) * 100.0}'"
        swap_result = execute_ssh_command(hostname, swap_cmd)
        if swap_result["success"] and swap_result["output"]:
            try:
                metrics["swap_percent"] = round(float(swap_result["output"].strip()), 1)
                logger.debug(f"Swap for {hostname}: {metrics['swap_percent']}%")
            except Exception as e:
                logger.warning(f"Failed to parse swap for {hostname}: {e}, output: {swap_result['output']}")
        
        # Get load average (1 minute) - simpler approach
        load_cmd = "uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | tr -d ','"
        load_result = execute_ssh_command(hostname, load_cmd)
        if load_result["success"] and load_result["output"]:
            try:
                metrics["load_avg"] = round(float(load_result["output"].strip()), 2)
                logger.debug(f"Load avg for {hostname}: {metrics['load_avg']}")
            except Exception as e:
                logger.warning(f"Failed to parse load avg for {hostname}: {e}, output: {load_result['output']}")
        
        # Determine if this is an app node or DB node
        is_app_node = hostname.startswith("jira-")
        is_db_node = hostname.startswith("db-")
        
        # Get local disk usage (/export for both app and DB nodes)
        disk_cmd = "df -h /export 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//'"
        disk_result = execute_ssh_command(hostname, disk_cmd)
        if not disk_result["success"] or not disk_result["output"]:
            # Fallback to root
            disk_cmd = "df -h / | tail -1 | awk '{print $5}' | sed 's/%//'"
            disk_result = execute_ssh_command(hostname, disk_cmd)
        
        if disk_result["success"] and disk_result["output"]:
            try:
                metrics["disk_usage_local"] = int(disk_result["output"].strip())
                logger.debug(f"Local disk usage for {hostname}: {metrics['disk_usage_local']}%")
            except Exception as e:
                logger.warning(f"Failed to parse local disk usage for {hostname}: {e}, output: {disk_result['output']}")
        
        # For app nodes: Get shared home disk usage
        if is_app_node:
            # Read cluster.properties to get jira.shared.home
            cluster_props_cmd = "cat /export/jirahome/cluster.properties 2>/dev/null | grep '^jira.shared.home' | cut -d'=' -f2 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//'"
            cluster_result = execute_ssh_command(hostname, cluster_props_cmd)
            
            if cluster_result["success"] and cluster_result["output"]:
                shared_home_path = cluster_result["output"].strip()
                logger.info(f"Found shared home path for {hostname}: '{shared_home_path}'")
                if shared_home_path:
                    # Get disk usage for shared home path
                    shared_disk_cmd = f"df -h '{shared_home_path}' 2>/dev/null | tail -1 | awk '{{print $5}}' | sed 's/%//'"
                    shared_disk_result = execute_ssh_command(hostname, shared_disk_cmd)
                    
                    logger.info(f"Shared disk command result for {hostname}: success={shared_disk_result['success']}, output='{shared_disk_result.get('output', 'None')}'")
                    
                    if shared_disk_result["success"] and shared_disk_result.get("output"):
                        output_stripped = shared_disk_result["output"].strip()
                        if output_stripped:
                            try:
                                disk_value = int(output_stripped)
                                metrics["disk_usage_shared_home"] = disk_value
                                logger.info(f"Shared home disk usage for {hostname}: {metrics['disk_usage_shared_home']}%")
                            except (ValueError, TypeError) as e:
                                logger.warning(f"Failed to parse shared home disk usage for {hostname}: {e}, output: '{output_stripped}'")
                                metrics["disk_usage_shared_home"] = "N/A"
                            except Exception as e:
                                logger.error(f"Unexpected error parsing shared home disk usage for {hostname}: {e}", exc_info=True)
                                metrics["disk_usage_shared_home"] = "N/A"
                        else:
                            logger.warning(f"Empty output from disk usage command for shared home path '{shared_home_path}' on {hostname}")
                            metrics["disk_usage_shared_home"] = "N/A"
                    else:
                        error_msg = shared_disk_result.get("error", "Unknown error")
                        logger.warning(f"Failed to get disk usage for shared home path '{shared_home_path}' on {hostname}: {error_msg}")
                        metrics["disk_usage_shared_home"] = "N/A"
                else:
                    logger.warning(f"Empty shared home path from cluster.properties on {hostname} (after strip)")
                    metrics["disk_usage_shared_home"] = "N/A"
            else:
                error_msg = cluster_result.get("error", "Unknown error") if not cluster_result["success"] else "No output"
                logger.warning(f"Failed to read cluster.properties or find jira.shared.home on {hostname}: {error_msg}")
                metrics["disk_usage_shared_home"] = "N/A"
        
        # For DB node: Get binlogs disk usage
        if is_db_node:
            binlogs_disk_cmd = "df -h /mysqllogs 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//'"
            binlogs_disk_result = execute_ssh_command(hostname, binlogs_disk_cmd)
            
            logger.info(f"Binlogs disk command result for {hostname}: success={binlogs_disk_result['success']}, output='{binlogs_disk_result.get('output', 'None')}'")
            
            if binlogs_disk_result["success"] and binlogs_disk_result.get("output"):
                output_stripped = binlogs_disk_result["output"].strip()
                if output_stripped:
                    try:
                        disk_value = int(output_stripped)
                        metrics["disk_usage_binlogs"] = disk_value
                        logger.info(f"Binlogs disk usage for {hostname}: {metrics['disk_usage_binlogs']}%")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse binlogs disk usage for {hostname}: {e}, output: '{output_stripped}'")
                        metrics["disk_usage_binlogs"] = "N/A"
                    except Exception as e:
                        logger.error(f"Unexpected error parsing binlogs disk usage for {hostname}: {e}", exc_info=True)
                        metrics["disk_usage_binlogs"] = "N/A"
                else:
                    logger.warning(f"Empty output from disk usage command for /mysqllogs on {hostname}")
                    metrics["disk_usage_binlogs"] = "N/A"
            else:
                error_msg = binlogs_disk_result.get("error", "Unknown error") if not binlogs_disk_result["success"] else "No output"
                logger.warning(f"Failed to get disk usage for /mysqllogs on {hostname}: {error_msg}")
                metrics["disk_usage_binlogs"] = "N/A"
        
        # Get DB connections count
        db_conn_cmd = "ss -ant 2>/dev/null | grep :3306 | wc -l"
        db_conn_result = execute_ssh_command(hostname, db_conn_cmd)
        if db_conn_result["success"] and db_conn_result["output"]:
            try:
                metrics["db_connections"] = int(db_conn_result["output"].strip())
                logger.debug(f"DB connections for {hostname}: {metrics['db_connections']}")
            except Exception as e:
                logger.warning(f"Failed to parse DB connections for {hostname}: {e}, output: {db_conn_result['output']}")
        
    except Exception as e:
        logger.error(f"Error collecting metrics from {hostname}: {str(e)}")
        metrics["status"] = "Error"
        metrics["error"] = str(e)
    
    logger.info(f"Completed metrics collection for {hostname}: CPU={metrics['cpu_percent']}, Memory={metrics['memory_percent']}, Load={metrics['load_avg']}")
    return metrics

# ========================================================================
# Database Metrics Functions
# ========================================================================

def get_db_connection_count_from_mysql():
    """Get total database connections from MySQL directly using read-only account."""
    # Re-read config to ensure we have latest values
    import config
    current_db_server = config.DB_SERVER
    current_db_connect_timeout = config.DB_CONNECT_TIMEOUT
    current_db_read_timeout = config.DB_READ_TIMEOUT
    current_db_max_connections = config.DB_MAX_CONNECTIONS
    
    logger.info(f"Connecting to MySQL database {current_db_server['db_name']} on {current_db_server['hostname']} as user {current_db_server['db_user']}")
    
    try:
        connection = pymysql.connect(
            host=current_db_server["hostname"],
            user=current_db_server["db_user"],
            password=current_db_server["db_password"],
            database=current_db_server["db_name"],
            connect_timeout=current_db_connect_timeout,
            read_timeout=current_db_read_timeout
        )
        logger.info(f"Successfully connected to MySQL database as {current_db_server['db_user']}")
        
        with connection.cursor() as cursor:
            # Get total connections
            logger.debug("Executing: SHOW STATUS LIKE 'Threads_connected'")
            cursor.execute("SHOW STATUS LIKE 'Threads_connected'")
            result = cursor.fetchone()
            total_connections = int(result[1]) if result else 0
            logger.debug(f"Threads_connected result: {total_connections}")
            
            # Get max connections
            logger.debug("Executing: SHOW VARIABLES LIKE 'max_connections'")
            cursor.execute("SHOW VARIABLES LIKE 'max_connections'")
            result = cursor.fetchone()
            max_connections = int(result[1]) if result else current_db_max_connections
            logger.debug(f"max_connections result: {max_connections}")
            
            # Get active queries
            logger.debug("Executing: SHOW PROCESSLIST")
            cursor.execute("SHOW PROCESSLIST")
            process_list = cursor.fetchall()
            active_queries = len([p for p in process_list if p[4] != 'Sleep'])
            logger.debug(f"Active queries (non-Sleep): {active_queries} out of {len(process_list)} total processes")
            
            # Get slow queries (if available)
            logger.debug("Executing: SHOW STATUS LIKE 'Slow_queries'")
            cursor.execute("SHOW STATUS LIKE 'Slow_queries'")
            result = cursor.fetchone()
            slow_queries = int(result[1]) if result else 0
            logger.debug(f"Slow_queries result: {slow_queries}")
        
        connection.close()
        logger.info(f"Database metrics collected successfully: {total_connections}/{max_connections} connections, {active_queries} active queries, {slow_queries} slow queries")
        
        return {
            "success": True,
            "total_connections": total_connections,
            "max_connections": max_connections,
            "active_queries": active_queries,
            "slow_queries": slow_queries,
            "connection_utilization": round((total_connections / max_connections) * 100, 1) if max_connections > 0 else 0
        }
    except pymysql.Error as e:
        logger.error(f"MySQL error connecting to database as {current_db_server['db_user']}: {str(e)} (Error code: {e.args[0] if e.args else 'N/A'})")
        return {
            "success": False,
            "error": f"MySQL Error: {str(e)}",
            "total_connections": 0,
            "max_connections": current_db_max_connections,
            "active_queries": 0,
            "slow_queries": 0,
            "connection_utilization": 0
        }
    except Exception as e:
        logger.error(f"Unexpected error connecting to database as {current_db_server['db_user']}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "total_connections": 0,
            "max_connections": current_db_max_connections,
            "active_queries": 0,
            "slow_queries": 0,
            "connection_utilization": 0
        }

def get_db_metrics():
    """Get comprehensive database metrics."""
    # Re-read config to ensure we have latest values
    import config
    current_db_server = config.DB_SERVER
    
    db_metrics = get_db_connection_count_from_mysql()
    
    # Also get system metrics from DB server
    db_system_metrics = get_system_metrics(current_db_server["hostname"])
    
    return {
        "db_metrics": db_metrics,
        "system_metrics": db_system_metrics
    }

# ========================================================================
# Threshold and Color Coding Functions
# ========================================================================

def get_color_class(value, thresholds, is_percentage=True):
    """Get color class based on threshold values."""
    if value == "N/A" or value is None:
        return "status-na"
    
    try:
        if is_percentage:
            val = float(value)
        else:
            val = float(value)
        
        if val < thresholds["green_max"]:
            return "status-green"
        elif val < thresholds["yellow_max"]:
            return "status-yellow"
        else:
            return "status-red"
    except:
        return "status-na"

def get_db_connection_color(connections, is_app_node=True):
    """Get color class for database connections."""
    # Re-read config to ensure we have latest values
    import config
    current_db_pool_per_app_node = config.DB_POOL_PER_APP_NODE
    current_db_max_connections = config.DB_MAX_CONNECTIONS
    current_db_connection_thresholds = config.DB_CONNECTION_THRESHOLDS
    
    if connections == "N/A" or connections is None:
        return "status-na"
    
    try:
        conn = int(connections)
        if is_app_node:
            max_conn = current_db_pool_per_app_node
        else:
            max_conn = current_db_max_connections
        
        utilization = conn / max_conn
        
        if utilization < current_db_connection_thresholds["green_max"]:
            return "status-green"
        elif utilization < current_db_connection_thresholds["yellow_max"]:
            return "status-yellow"
        else:
            return "status-red"
    except:
        return "status-na"

# ========================================================================
# Main Health Check Function
# ========================================================================

def check_all_health():
    """Check health of all systems."""
    logger.info("Starting comprehensive health check")
    
    # Re-read config values from config module to ensure we have latest
    import config
    current_jira_servers = config.JIRA_SERVERS
    current_jira_pat = config.JIRA_PAT
    current_db_server = config.DB_SERVER
    current_auto_refresh_interval = config.AUTO_REFRESH_INTERVAL
    
    logger.info(f"Using {len(current_jira_servers)} Jira servers, DB server: {current_db_server.get('hostname', 'N/A')}")
    
    start_time = datetime.datetime.now()
    
    results = {
        "index_health": [],
        "system_metrics": [],
        "db_connections": [],
        "db_metrics": None,
        "last_update": start_time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    try:
        # Get Jira index health
        logger.info("Fetching Jira index health...")
        for server in current_jira_servers:
            report = fetch_jira_health(server["name"], server["url"], current_jira_pat)
            results["index_health"].append(report)
        
        # Get system metrics for app nodes
        logger.info("Collecting system metrics from app nodes...")
        for server in current_jira_servers:
            metrics = get_system_metrics(server["hostname"])
            metrics["server_name"] = server["name"]
            results["system_metrics"].append(metrics)
            results["db_connections"].append({
                "server_name": server["name"],
                "hostname": server["hostname"],
                "connections": metrics["db_connections"],
                "status": metrics["status"]
            })
        
        # Get database metrics
        logger.info("Collecting database metrics...")
        results["db_metrics"] = get_db_metrics()
        
        # Add DB server to system metrics
        db_system = results["db_metrics"]["system_metrics"]
        db_system["server_name"] = current_db_server["name"]
        results["system_metrics"].append(db_system)
        
        # Add DB server to connections list
        db_total_conn = results["db_metrics"]["db_metrics"]["total_connections"]
        results["db_connections"].append({
            "server_name": current_db_server["name"],
            "hostname": current_db_server["hostname"],
            "connections": db_total_conn,
            "status": db_system["status"]
        })
        
        elapsed = (datetime.datetime.now() - start_time).total_seconds()
        logger.info(f"Health check completed in {elapsed:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error during health check: {str(e)}", exc_info=True)
    
    return results

# ========================================================================
# Flask Routes
# ========================================================================

@app.route('/')
def index():
    """Renders the main page without loading data initially."""
    logger.info("Health Dashboard index route called")
    # Re-read config to ensure we have latest values
    import health_dashboard_config as config
    current_auto_refresh_interval = config.AUTO_REFRESH_INTERVAL
    
    # Use explicit template path to ensure correct template is loaded
    template_path = os.path.join(framework_dir, 'templates', 'index.html')
    logger.info(f"Health Dashboard rendering template from: {template_path}")
    
    # Read the template file directly to ensure we get the correct one
    import jinja2
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
        results=None,
        refresh_interval=current_auto_refresh_interval
    )

@app.route('/check-health')
def check_health():
    """Manual health check endpoint."""
    # Re-read config to ensure we have latest values
    import health_dashboard_config as config
    current_auto_refresh_interval = config.AUTO_REFRESH_INTERVAL
    results = check_all_health()
    # Use explicit template path to ensure correct template is loaded
    template_path = os.path.join(framework_dir, 'templates', 'index.html')
    
    # Read the template file directly to ensure we get the correct one
    import jinja2
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
        results=results,
        refresh_interval=current_auto_refresh_interval
    )

@app.route('/api/health')
def api_health():
    """JSON API endpoint for health data (for auto-refresh)."""
    results = check_all_health()
    return jsonify(results)

if __name__ == '__main__':
    # Runs the app. 'debug=True' reloads the app on code changes.
    # 'host=0.0.0.0' makes it accessible on your network, not just localhost.
    app.run(debug=True, host='0.0.0.0', port=5001)
