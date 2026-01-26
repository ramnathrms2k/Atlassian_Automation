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
PROJ_KEY = "GLTS" 

print(f"🔍 Checking Project: {PROJ_KEY}...")

# 2. Get Project Definition (Verified Method for Jira 9+)
url = f"{base_url}/rest/api/2/project/{PROJ_KEY}"
r = requests.get(url, headers=headers)

if r.status_code != 200:
    print(f"❌ Error fetching project: {r.status_code}")
    print(r.text)
    sys.exit(1)

data = r.json()
print(f"✅ Project Found: {data['name']} (ID: {data['id']})")
print(f"   Style: {data.get('projectTypeKey', 'Unknown')}")

# 3. List Issue Types
print("\n📋 VALID ISSUE TYPES:")
found_types = []
for it in data["issueTypes"]:
    print(f"   - Name: {it['name']:<15} | ID: {it['id']}")
    found_types.append(it)

# 4. Attempt a Dry Run Create (using the first valid type found)
if not found_types:
    print("❌ No issue types found!")
    sys.exit(1)

# Prefer 'Story' or 'Bug', otherwise take the first one
target = next((t for t in found_types if t['name'] in ['Story', 'Bug']), found_types[0])

print("-" * 40)
print(f"🛠  Test Create with Type: '{target['name']}' (ID: {target['id']})")

payload = {
    "fields": {
        "project": {"key": PROJ_KEY},
        "summary": "Smoke Test - Debug Project",
        "issuetype": {"id": str(target['id'])}
    }
}

r_create = requests.post(f"{base_url}/rest/api/2/issue", json=payload, headers=headers)

if r_create.status_code == 201:
    key = r_create.json()['key']
    print(f"🎉 SUCCESS! Created {key}")
    requests.delete(f"{base_url}/rest/api/2/issue/{key}", headers=headers)
    print(f"   (Deleted {key} cleanup)")
    print(f"\n✅ ACTION: Update discover.py -> 'issue_type_id': '{target['id']}'")
else:
    print(f"❌ CREATE FAILED: {r_create.status_code}")
    print(json.dumps(r_create.json(), indent=2))
