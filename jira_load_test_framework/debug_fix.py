import json
import requests
import sys

# 1. Load Config
try:
    with open("config.json", "r") as f:
        cfg = json.load(f)
        env = cfg["environments"]["dev"]
        base_url = env["base_url"]
        token = env["tokens"][0]
except Exception as e:
    print(f"❌ Config Error: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
PROJ_KEY = "GTLS" 

print(f"🔍 DIAGNOSTIC MODE: {base_url}")
print("-" * 60)

# --- CHECK 1: CREATE ISSUE ---
print(f"1. Checking Create Issue Meta for Project '{PROJ_KEY}'...")
# Use the Project API which is reliable in Jira 9/10
url = f"{base_url}/rest/api/2/project/{PROJ_KEY}"
r = requests.get(url, headers=headers)

if r.status_code == 200:
    data = r.json()
    print(f"   ✅ Project Found: {data['name']} (ID: {data['id']})")
    print("   📋 Valid Issue Types:")
    
    valid_id = None
    for it in data["issueTypes"]:
        print(f"      - {it['name']:<15} ID: {it['id']}")
        # Prefer 'Story'
        if it['name'] == "Story": valid_id = it['id']
    
    if not valid_id: valid_id = data["issueTypes"][0]["id"]
    
    print(f"\n   🛠  Attempting Create with ID: {valid_id}...")
    payload = {
        "fields": {
            "project": {"key": PROJ_KEY},
            "summary": "Smoke Test Fix",
            "issuetype": {"id": str(valid_id)}
        }
    }
    r_create = requests.post(f"{base_url}/rest/api/2/issue", json=payload, headers=headers)
    
    if r_create.status_code == 201:
        print(f"   🎉 SUCCESS! Issue Created: {r_create.json()['key']}")
        print(f"   👉 FIX FOR DISCOVER.PY: Set 'issue_type_id': '{valid_id}'")
        # Cleanup
        requests.delete(f"{base_url}/rest/api/2/issue/{r_create.json()['key']}", headers=headers)
    else:
        print(f"   ❌ FAILED: {r_create.status_code}")
        print(f"   ⚠️  ERROR: {r_create.text}")
else:
    print(f"   ❌ Project Lookup Failed: {r.status_code}")

print("-" * 60)

# --- CHECK 2: PORTFOLIO PLANS ---
print("2. Checking Portfolio / Plans Execution Endpoint...")
# First, find a plan
r_plans = requests.get(f"{base_url}/rest/roadmap/1.0/plans", headers=headers)
plan_id = None
if r_plans.status_code == 200 and "collection" in r_plans.json():
    plans = r_plans.json()["collection"]
    if plans:
        plan_id = plans[0]["id"]
        print(f"   ✅ Found Plan ID: {plan_id}")
    else:
        print("   ⚠️  No plans found to test.")

if plan_id:
    # Test the URL currently in locustfile.py
    old_url = f"/rest/jpo/1.0/plan/{plan_id}/hierarchy"
    print(f"   Testing OLD URL (Locust): {old_url}")
    r_old = requests.post(f"{base_url}{old_url}", json={}, headers=headers)
    print(f"   👉 Status: {r_old.status_code}")

    # Test the NEW URL (Recommendation)
    new_url = f"/rest/roadmap/1.0/plans/{plan_id}"
    print(f"   Testing NEW URL (Proposed): {new_url}")
    r_new = requests.get(f"{base_url}{new_url}", headers=headers)
    print(f"   👉 Status: {r_new.status_code}")
    
    if r_new.status_code == 200:
        print(f"\n   👉 FIX FOR LOCUSTFILE.PY: Change task to use '{new_url}'")
