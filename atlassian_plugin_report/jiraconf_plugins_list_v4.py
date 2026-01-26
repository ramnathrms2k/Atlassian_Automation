import requests
import json
import warnings
import csv
import datetime

# --- Configuration ---

# Get today's date for the filename
TODAY = datetime.datetime.now().strftime('%Y-%m-%d')
CSV_FILENAME = f"plugin_report_{TODAY}.csv"

# Define the headers for your CSV file.
# These keys MUST match the keys in the dictionary created in get_paid_apps
CSV_HEADERS = [
    "Server Name", 
    "Host SEN",               # <-- ★ NEW ★
    "App Name", 
    "License Tier", 
    "License Status", 
    "Maintenance Expiry", 
    "SEN",                    # This is the App's SEN
    "Marketplace URL", 
    "App Key"
]

# Suppress only the InsecureRequestWarning from unverified HTTPS requests
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

# Define your Jira/Confluence instances. 
# Use Personal Access Tokens (PATs) for security.
SERVERS = [
    {
        "name": "Jira-Prod",
        "url": "https://vmw-jira.broadcom.net",
        "token": "TOKEN" 
    },
    {
        "name": "Confluence-Prod",
        "url": "https://vmw-confluence.broadcom.net",
        "token": "TOKEN"
    }
    # Add more servers here
]

# UPM API endpoint to find marketplace apps
API_ENDPOINT = "/rest/plugins/1.0/installed-marketplace"

# --- Main Function ---

def get_paid_apps(base_url, token, server_name):
    """
    Connects to an instance and returns a list of dictionaries
    containing paid app license details.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "*/*"  # Avoid 406 Not Acceptable errors
    }
    
    paid_apps_list = []
    
    try:
        # Set verify=False to ignore SSL certificate errors
        response = requests.get(
            base_url + API_ENDPOINT, 
            headers=headers, 
            timeout=10, 
            verify=False 
        )
        
        # Check for successful response
        response.raise_for_status()
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"  [ERROR] Response for {server_name} ({base_url}) was not valid JSON.")
            return []

        # --- ★ NEW ★ ---
        # Get the parent application's (Host) SEN
        host_status = data.get('hostStatus', {})
        host_license = host_status.get('hostLicense', {})
        host_sen = host_license.get('supportEntitlementNumber', 'N/A')
        # --- End New ---

        for plugin in data.get('plugins', []):
            # A plugin is considered "paid" if it has the licenseDetails object
            license_details = plugin.get('licenseDetails')
            
            if license_details:
                
                # Get license status
                is_valid = license_details.get('valid')
                status = "VALID"
                if not is_valid:
                    # Will grab "EXPIRED" or "INVALID"
                    status = license_details.get('error', 'INVALID') 
                
                app_key = plugin.get('key')
                
                # Create a dictionary. Keys MUST match CSV_HEADERS.
                app_data = {
                    "Server Name": server_name,
                    "Host SEN": host_sen,  # <-- ★ NEW ★
                    "App Name": plugin.get('name'),
                    "App Key": app_key,
                    "License Tier": license_details.get('maximumNumberOfUsers', 'Unknown Tier'),
                    "License Status": status,
                    "Maintenance Expiry": license_details.get('maintenanceExpiryDateString', 'N/A'),
                    "SEN": license_details.get('supportEntitlementNumber', 'N/A'), # App SEN
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
    
    all_paid_apps = []

    for server in SERVERS:
        print(f"--- Checking Server: {server['name']} ({server['url']}) ---")
        
        apps = get_paid_apps(server['url'], server['token'], server['name'])
        
        if apps:
            print(f"  Found {len(apps)} paid apps.")
            all_paid_apps.extend(apps)
        else:
            print("  No paid apps found (or an error occurred).\n")
    
    # --- Write to CSV ---
    if all_paid_apps:
        # Sort the final list by Server Name, then App Name
        all_paid_apps.sort(key=lambda x: (x['Server Name'], x['App Name']))
        
        try:
            with open(CSV_FILENAME, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=CSV_HEADERS)
                
                writer.writeheader()
                writer.writerows(all_paid_apps)
                
            print(f"\n--- Report Complete ---")
            print(f"✅ Success! Report saved to '{CSV_FILENAME}'")
            print("Next step: Open the CSV and use the URLs for manual price checks.")

        except IOError as e:
            print(f"\n[FATAL ERROR] Could not write to file '{CSV_FILENAME}'.")
            print(f"Error: {e}")
            print("Please check directory permissions.")
            
    else:
        print("\n--- Report Complete ---")
        print("No paid apps were found on any server. No CSV file generated.")
