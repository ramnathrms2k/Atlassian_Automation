import requests
import json
import random
import sys
import logging
import datetime
import argparse
import os

# --- ARGUMENT PARSING ---
parser = argparse.ArgumentParser(description="Jira Discovery Script")
parser.add_argument("--env", required=True, help="Environment key (sandbox, dev)")
parser.add_argument("--profile", required=True, help="Test Profile (resiliency, longevity)")
parser.add_argument("--run_id", required=True, help="Unique Test Identifier")
args = parser.parse_args()

RUN_ID = args.run_id
ENV_KEY = args.env
PROFILE_KEY = args.profile

# --- CONFIG LOADING ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
try:
    with open("config.json", "r") as f:
        FULL_CONFIG = json.load(f)
        ENV_CONFIG = FULL_CONFIG["environments"][ENV_KEY]
        LIMITS = FULL_CONFIG["profiles"][PROFILE_KEY]["discovery_params"]
except KeyError as e:
    logging.error(f"Config Key Error: {e}")
    sys.exit(1)
except FileNotFoundError:
    logging.error("config.json not found.")
    sys.exit(1)

BASE_URL = ENV_CONFIG["base_url"]
TOKENS = ENV_CONFIG["tokens"]

# --- HARDCODED FALLBACKS ---
FALLBACK_CREATE_META = {
    "key": "GTLS1",        # Corrected Project Key
    "issue_type_id": "3" # Standard Story ID
}

# --- YOUR MANUAL ID ---
FALLBACK_RICH_FILTER_ID = "11203" 

def get_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Atlassian-Token": "no-check"
    }

def try_endpoints(resource_name, endpoints, limit=50):
    for endpoint in endpoints:
        for token in TOKENS:
            try:
                connector = "&" if "?" in endpoint else "?"
                url = f"{BASE_URL}{endpoint}{connector}maxResults={limit}"
                
                resp = requests.get(url, headers=get_headers(token), timeout=10)
                
                if resp.status_code == 200 and "<html" in resp.text.lower():
                    continue 

                if resp.status_code == 200:
                    data = resp.json()
                    items = []
                    
                    if isinstance(data, list): items = data
                    elif "values" in data: items = data["values"]
                    elif "plans" in data: items = data["plans"]
                    elif "structures" in data: items = data["structures"]
                    elif "dashboards" in data: items = data["dashboards"]
                    
                    # --- PORTFOLIO FIX ---
                    elif "collection" in data: items = data["collection"]
                    # ---------------------
                    
                    if items:
                        logging.info(f"  [{resource_name}] SUCCESS. Found {len(items)} items.")
                        return items[:limit]
            except Exception: 
                pass
    
    logging.warning(f"  [{resource_name}] Failed to find data via API.")
    return []

def discover():
    logging.info(f"--- Starting Discovery | Env: {ENV_KEY} | Profile: {PROFILE_KEY} ---")
    
    issues = []
    try:
        h = get_headers(random.choice(TOKENS))
        max_fetch = LIMITS['max_issues']
        # Simplified fetch to avoid offset errors on small projects
        resp = requests.get(f"{BASE_URL}/rest/api/2/search?jql=created is not EMPTY&maxResults={max_fetch}&fields=key", headers=h)
        issues = [i["key"] for i in resp.json().get("issues", [])]
        logging.info(f"  [Issues] Successfully loaded {len(issues)} keys.")
    except Exception as e: 
        logging.error(f"  [Issues] Failed: {e}")

    create_meta = [FALLBACK_CREATE_META]
    
    dashboards = try_endpoints("Dashboards", ["/rest/api/2/dashboard/search", "/rest/api/2/dashboard"], limit=30)
    boards = try_endpoints("Boards", ["/rest/agile/1.0/board?type=scrum", "/rest/agile/1.0/board"], limit=50)
    structures = try_endpoints("Structure", ["/rest/structure/2.0/structure", "/rest/structure/1.0/structure"], limit=50)
    plans = try_endpoints("Portfolio Plans", ["/rest/roadmap/1.0/plans", "/rest/jpo/1.0/plan"], limit=30)
    tempo_teams = try_endpoints("Tempo Teams", ["/rest/tempo-teams/2/team", "/rest/tempo-teams/1/team"], limit=50)
    
    # --- RICH FILTERS: FORCE FALLBACK ---
    # We skip the API check to ensure we use the ID you know works
    rich_filter_ids = [FALLBACK_RICH_FILTER_ID]
    logging.info(f"  [Rich Filters] Using Hardcoded ID: {FALLBACK_RICH_FILTER_ID}")

    filters = try_endpoints("Filters", ["/rest/api/2/filter/search?ordering=-favouriteCount", "/rest/api/2/filter/favourite"], limit=50)
    jql_queries = [f["jql"] for f in filters if "jql" in f]

    data = {
        "run_id": RUN_ID,
        "env": ENV_KEY,
        "profile": PROFILE_KEY,
        "meta_run_date": str(datetime.datetime.now()),
        "issues": issues,
        "create_meta": create_meta,
        "dashboards": [d["id"] for d in dashboards],
        "boards": [b["id"] for b in boards],
        "structures": [s["id"] for s in structures],
        "plans": [p["id"] for p in plans],
        "tempo_teams": [t["id"] for t in tempo_teams],
        "rich_filters": rich_filter_ids,
        "jql_queries": jql_queries
    }

    json_filename = f"data_{RUN_ID}.json"
    with open(json_filename, "w") as f:
        json.dump(data, f, indent=2)
        
    logging.info(f"--- Discovery Complete. Files saved with suffix: _{RUN_ID} ---")

if __name__ == "__main__":
    discover()
