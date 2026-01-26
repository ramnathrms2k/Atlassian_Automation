import requests
import json
import warnings
import csv
import datetime
import sys

# --- Configuration ---

# Get today's date for the filename and report
TODAY = datetime.date.today()
TODAY_STRING = TODAY.strftime('%Y-%m-%d')
CSV_FILENAME = f"plugin_report_{TODAY_STRING}.csv"
CONFIG_FILENAME = "servers_config.json"

# Define the headers for your CSV file.
CSV_HEADERS = [
    "Report Date",            # <-- NEW
    "Server Name", 
    "Host SEN",
    "Host User Tier",
    "Host Expiry Date",
    "Host Days to Expiry",    # <-- NEW
    "App Name", 
    "License Tier", 
    "License Status", 
    "Maintenance Expiry",     # This is the App's Expiry
    "App Days to Expiry",     # <-- NEW
    "SEN",                    # This is the App's SEN
    "Marketplace URL", 
    "App Key"
]

# Suppress only the InsecureRequestWarning from unverified HTTPS requests
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# UPM API endpoint to find marketplace apps
API_ENDPOINT = "/rest/plugins/1.0/installed-marketplace"

# --- Helper Functions ---

def parse_expiry_date(date_str):
    """
    Parses multiple different date formats from the Atlassian API.
    Formats seen: "May 31, 2026", "31/May/26", "19 Dec 2024", "Aug 08, 2024"
    """
    if not date_str or date_str == 'N/A':
        return None
    
    # List of possible formats
    formats_to_try = [
        '%B %d, %Y',  # "May 31, 2026"
        '%d/%b/%y',   # "31/May/26"
        '%d %b %Y',   # "19 Dec 2024"
        '%b %d, %Y',   # "Aug 08, 2024"
        '%Y-%m-%d',   # "2025-11-07"
    ]
    
    for fmt in formats_to_try:
        try:
            # strptime returns a datetime object, we convert to date
            return datetime.datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue # Try the next format
            
    # If all formats fail
    print(f"  [WARN] Could not parse unknown date format: {date_str}")
    return None

def calculate_days_to_expiry(expiry_date):
    """
    Calculates the number of days left until the expiry date.
    Returns 0 if the date is in the past.
    """
    if expiry_date is None:
        return "N/A"
        
    days_delta = (expiry_date - TODAY).days
    
    # If expired, show 0 days left, not a negative number
    if days_delta < 0:
        return 0
    return days_delta

def load_config(filename):
    """
    Loads the server configuration from a JSON file.
    """
    try:
        with open(filename, 'r') as f:
            config_data = json.load(f)
            if 'servers' not in config_data:
                print(f"[FATAL ERROR] Config file '{filename}' is missing the 'servers' key.")
                sys.exit(1)
            return config_data['servers']
    except FileNotFoundError:
        print(f"[FATAL ERROR] Config file '{filename}' not found.")
        print("Please create it and add your server details.")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"[FATAL ERROR] Config file '{filename}' is not valid JSON.")
        sys.exit(1)
    except Exception as e:
        print(f"[FATAL ERROR] An error occurred loading config: {e}")
        sys.exit(1)

# --- Main Work Function ---

def get_paid_apps(base_url, token, server_name):
    """
    Connects to an instance and returns a list of dictionaries
    containing paid app license details.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "*/*"
    }
    
    paid_apps_list = []
    
    try:
        response = requests.get(
            base_url + API_ENDPOINT, 
            headers=headers, 
            timeout=10, 
            verify=False 
        )
        response.raise_for_status()
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"  [ERROR] Response for {server_name} ({base_url}) was not valid JSON.")
            return []

        # Get the parent application's (Host) license details
        host_status = data.get('hostStatus', {})
        host_license = host_status.get('hostLicense', {})
        host_sen = host_license.get('supportEntitlementNumber', 'N/A')
        host_user_tier = host_license.get('maximumNumberOfUsers', 'N/A')
        
        # --- ★ BUG FIX ★ ---
        # Try 'maintenanceExpiryDateString' first, then fall back to 'expiryDateString'
        host_expiry_str = host_license.get('maintenanceExpiryDateString')
        if not host_expiry_str or host_expiry_str == 'N/A':
            host_expiry_str = host_license.get('expiryDateString', 'N/A')
        
        # --- ★ NEW FEATURE ★ ---
        host_expiry_date = parse_expiry_date(host_expiry_str)
        host_days_left = calculate_days_to_expiry(host_expiry_date)
        # --- End New Feature ---

        for plugin in data.get('plugins', []):
            license_details = plugin.get('licenseDetails')
            
            if license_details:
                is_valid = license_details.get('valid')
                status = "VALID"
                if not is_valid:
                    status = license_details.get('error', 'INVALID') 
                
                app_key = plugin.get('key')
                
                # --- ★ NEW FEATURE ★ ---
                app_expiry_str = license_details.get('maintenanceExpiryDateString', 'N/A')
                app_expiry_date = parse_expiry_date(app_expiry_str)
                app_days_left = calculate_days_to_expiry(app_expiry_date)
                # --- End New Feature ---
                
                app_data = {
                    "Report Date": TODAY_STRING,
                    "Server Name": server_name,
                    "Host SEN": host_sen,
                    "Host User Tier": host_user_tier,
                    "Host Expiry Date": host_expiry_str,
                    "Host Days to Expiry": host_days_left,
                    "App Name": plugin.get('name'),
                    "App Key": app_key,
                    "License Tier": license_details.get('maximumNumberOfUsers', 'Unknown Tier'),
                    "License Status": status,
                    "Maintenance Expiry": app_expiry_str,
                    "App Days to Expiry": app_days_left,
                    "SEN": license_details.get('supportEntitlementNumber', 'N/A'),
                    "Marketplace URL": f"https://marketplace.atlassian.com/plugins/{app_key}"
                }
                paid_apps_list.append(app_data)
                
    except requests.exceptions.HTTPError as e:
        print(f"  [ERROR] HTTP Error for {server_name}: {e.response.status_code}")
        if e.response.status_code == 401:
            print("  [HINT] Received 401 Unauthorized. Check your Personal Access Token (PAT).")
    except requests.exceptions.ConnectionError as e:
        print(f"  [ERROR] Connection Error for {server_name}: Could not connect.")
    except Exception as e:
        print(f"  [ERROR] An unknown error occurred for {server_name}: {e}")
        
    return paid_apps_list

# --- Run The Script ---

if __name__ == "__main__":
    print(f"Starting plugin budget report... (Will save to {CSV_FILENAME})\n")
    
    servers_to_check = load_config(CONFIG_FILENAME)
    all_paid_apps = []

    for server in servers_to_check:
        print(f"--- Checking Server: {server['name']} ({server['url']}) ---")
        
        apps = get_paid_apps(server['url'], server['token'], server['name'])
        
        if apps:
            print(f"  Found {len(apps)} paid apps.")
            all_paid_apps.extend(apps)
        else:
            print("  No paid apps found (or an error occurred).\n")
    
    # --- Write to CSV ---
    if all_paid_apps:
        all_paid_apps.sort(key=lambda x: (x['Server Name'], x['App Name']))
        
        try:
            with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
                writer.writeheader()
                writer.writerows(all_paid_apps)
                
            print(f"\n--- Report Complete ---")
            print(f"✅ Success! Report saved to '{CSV_FILENAME}'")
            print("You can now open the CSV to sort by 'Host Days to Expiry' or 'App Days to Expiry'.")

        except IOError as e:
            print(f"\n[FATAL ERROR] Could not write to file '{CSV_FILENAME}'. Error: {e}")
            
    else:
        print("\n--- Report Complete ---")
        print("No paid apps were found on any server. No CSV file generated.")
