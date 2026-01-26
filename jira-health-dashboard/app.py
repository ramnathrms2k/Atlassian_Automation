import requests
import datetime
from flask import Flask, render_template
from config import JIRA_SERVERS, JIRA_PAT

# Initialize the Flask app
app = Flask(__name__)

def fetch_jira_health(server_name, base_url, pat):
    """Fetches the index summary from a single Jira server."""
    
    api_url = f"{base_url}/rest/api/2/index/summary"
    headers = {
        'Authorization': f'Bearer {pat}',
        'Accept': 'application/json'
    }
    
    start_time = datetime.datetime.now()
    
    try:
        # Set a reasonable timeout (e.g., 10 seconds)
        response = requests.get(api_url, headers=headers, timeout=10)
        
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

@app.route('/')
def index():
    """Renders the main page with just the button."""
    return render_template('index.html', results=None)

@app.route('/check-health')
def check_health():
    """
    This is the endpoint the button clicks. 
    It runs the checks and re-renders the page with the results table.
    """
    health_reports = []
    for server in JIRA_SERVERS:
        report = fetch_jira_health(server["name"], server["url"], JIRA_PAT)
        health_reports.append(report)
        
    # Pass the list of reports to the HTML template
    return render_template('index.html', results=health_reports)

if __name__ == '__main__':
    # Runs the app. 'debug=True' reloads the app on code changes.
    # 'host=0.0.0.0' makes it accessible on your network, not just localhost.
    app.run(debug=True, host='0.0.0.0', port=5001)
