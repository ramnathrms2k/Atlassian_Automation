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

def probe(name, urls):
    print(f"\n🔎 Probing {name}...")
    for url in urls:
        full_url = f"{base_url}{url}"
        print(f"   Trying: {url}")
        try:
            r = requests.get(full_url, headers=headers, timeout=5)
            print(f"   Status: {r.status_code}")
            if r.status_code == 200:
                try:
                    data = r.json()
                    # Print snippet of data to see structure
                    print(f"   ✅ RESPONSE PAYLOAD: {str(data)[:200]}...") 
                    return
                except:
                    print("   ⚠️  Response not JSON")
            else:
                print(f"   ❌ Failed: {r.text[:100]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

# --- 1. RICH FILTERS PROBE ---
# We try the standard API and the config API
rf_endpoints = [
    "/rest/rich-filters/1.0/filter",
    "/rest/rich-filters/1.0/richFilter",
    "/rest/rich-filters/latest/filter"
]
probe("Rich Filters", rf_endpoints)

# --- 2. PORTFOLIO / PLANS PROBE ---
# We try Advanced Roadmaps (JPO) and new Plans 
plan_endpoints = [
    "/rest/jpo/1.0/plan",
    "/rest/roadmap/1.0/plans",
    "/rest/jpo/1.0/plan/all" 
]
probe("Portfolio Plans", plan_endpoints)
