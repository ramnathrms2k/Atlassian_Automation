import json
import requests
import sys

# 1. Load Config to get URL/Token
try:
    with open("config.json", "r") as f:
        cfg = json.load(f)
        # Assuming 'dev' environment
        env = cfg["environments"]["dev"]
        base_url = env["base_url"]
        token = env["tokens"][0]
except Exception as e:
    print(f"❌ Could not load config.json: {e}")
    sys.exit(1)

headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
PROJ_KEY = "GLTS" # The project we are debugging

# 2. Inspect Meta Data
print(f"🔍 Inspecting Project: {PROJ_KEY}...")
meta_url = f"{base_url}/rest/api/2/issue/createmeta?projectKeys={PROJ_KEY}&expand=projects.issuetypes.fields"
r = requests.get(meta_url, headers=headers)

if r.status_code != 200:
    print(f"❌ Failed to fetch meta: {r.status_code} {r.text}")
    sys.exit(1)

data = r.json()
if not data.get("projects"):
    print(f"❌ Project {PROJ_KEY} not found or user has no CREATE permission.")
    sys.exit(1)

project = data["projects"][0]
print(f"✅ Found Project: {project['name']} (ID: {project['id']})")
print("\n📋 Available Issue Types:")

target_id = "1" # This is what we tried last time
found_target = False
suggested_id = None

for it in project["issuetypes"]:
    print(f"   - Name: {it['name']:<15} | ID: {it['id']}")
    if str(it['id']) == target_id:
        found_target = True
    # Suggest 'Story' or 'Bug' if we haven't found one
    if not suggested_id and it['name'] in ['Story', 'Bug', 'Task']:
        suggested_id = it['id']

print("-" * 40)

# 3. Test Creation
id_to_test = target_id if found_target else suggested_id
if not id_to_test:
    print("❌ No suitable Issue Type found!")
    sys.exit(1)

print(f"🛠  Attempting to create issue with ID: {id_to_test}...")

payload = {
    "fields": {
        "project": {"key": PROJ_KEY},
        "summary": "Smoke Test - Debug Script",
        "issuetype": {"id": str(id_to_test)}
    }
}

r = requests.post(f"{base_url}/rest/api/2/issue", json=payload, headers=headers)

if r.status_code == 201:
    key = r.json()['key']
    print(f"🎉 SUCCESS! Issue Created: {key}")
    # Cleanup
    requests.delete(f"{base_url}/rest/api/2/issue/{key}", headers=headers)
    print("   (Issue deleted to keep project clean)")
    print(f"\n✅ ACTION: Update discover.py -> set 'issue_type_id': '{id_to_test}'")
else:
    print(f"❌ FAILURE: Status {r.status_code}")
    print("   Server Response:")
    print(json.dumps(r.json(), indent=2))
    print("\n⚠️ ACTION: Look at the 'errors' above. You are likely missing a mandatory field.")
