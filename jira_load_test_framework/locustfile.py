import os
import sys
import json
import random
import logging
import uuid
import time
from locust import HttpUser, task, between, LoadTestShape, events

RUN_ID = os.environ.get("RUN_ID", "default")
TARGET_ENV = os.environ.get("TARGET_ENV", "dev")
TEST_PROFILE = os.environ.get("TEST_PROFILE", "resiliency")

logger = logging.getLogger("locust_logger")
logger.setLevel(logging.INFO)
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S"))
logger.addHandler(sh)

try:
    with open("config.json", "r") as f:
        FULL_CONFIG = json.load(f)
        ENV_CONFIG = FULL_CONFIG["environments"][TARGET_ENV]
        PROFILE_CONFIG = FULL_CONFIG["profiles"][TEST_PROFILE]
        RATIOS = FULL_CONFIG["ratios"]
        
    data_file = f"data_{RUN_ID}.json"
    with open(data_file, "r") as f:
        TEST_DATA = json.load(f)
except Exception as e:
    logger.error(f"CRITICAL: Failed to load config or data ({e}).")
    sys.exit(1)

TOKENS = ENV_CONFIG["tokens"]
BASE_URL = ENV_CONFIG["base_url"]
TARGET_USERS = ENV_CONFIG["limits"][TEST_PROFILE]

SHARED_CREATED_ISSUES = []

@events.test_start.add_listener
def log_metadata(**kwargs):
    logger.info("=" * 60)
    logger.info(f"🚀 LAUNCHING PROFILE: {TEST_PROFILE.upper()} on {TARGET_ENV.upper()}")
    logger.info("=" * 60)
    logger.info(f"🆔 Run ID:        {RUN_ID}")
    logger.info(f"⚖️  Ratios:        Read {RATIOS['read_weight']}% / Write {RATIOS['write_weight']}%")
    logger.info("-" * 60)

class JiraBaseUser(HttpUser):
    abstract = True  # <--- FIX APPLIED
    host = BASE_URL
    wait_time = between(2, 5)

    def on_start(self):
        self.token = random.choice(TOKENS)
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    def get_headers(self):
        return {"X-Correlation-ID": str(uuid.uuid4()), "Content-Type": "application/json", "Accept": "application/json"}

class JiraReadUser(JiraBaseUser):
    # Weights optimized for Realistic Simulation
    @task(40)
    def read_01_view_issue_baseline(self):
        if not TEST_DATA["issues"]: return
        issue_key = random.choice(TEST_DATA["issues"])
        self.client.get(f"/rest/api/2/issue/{issue_key}", headers=self.get_headers(), name="Read_01_View_Issue_Baseline")

    @task(2)
    def read_01b_view_issue_freshly_created(self):
        if SHARED_CREATED_ISSUES:
            issue_key = random.choice(SHARED_CREATED_ISSUES)
            self.client.get(f"/rest/api/2/issue/{issue_key}", headers=self.get_headers(), name="Read_01b_View_Issue_Fresh")

    @task(10)
    def read_02_view_agile_board(self):
        if not TEST_DATA.get("boards"): return
        b_id = random.choice(TEST_DATA["boards"])
        self.client.get(f"/rest/agile/1.0/board/{b_id}/issue", headers=self.get_headers(), name="Read_02_View_Agile_Board")

    @task(8)
    def read_03_search_jql_standard(self):
        if not TEST_DATA["jql_queries"]: return
        jql = random.choice(TEST_DATA["jql_queries"])
        self.client.get(f"/rest/api/2/search?jql={jql}&maxResults=20", headers=self.get_headers(), name="Read_03_Search_JQL_Standard")

    @task(2)
    def read_04_search_jql_scriptrunner_complex(self):
        jql = "issueFunction in hasLinks('blocks')" 
        self.client.get(f"/rest/api/2/search?jql={jql}&maxResults=15", headers=self.get_headers(), name="Read_04_Search_JQL_ScriptRunner")

    @task(5)
    def read_05_view_dashboard_gadgets(self):
        if not TEST_DATA.get("dashboards"): return
        d_id = random.choice(TEST_DATA["dashboards"])
        self.client.get(f"/rest/api/2/dashboard/{d_id}", headers=self.get_headers(), name="Read_05_View_Dashboard")

    @task(1)
    def read_06_plugin_structure_forest(self):
        if not TEST_DATA.get("structures"): return
        s_id = random.choice(TEST_DATA["structures"])
        self.client.post("/rest/structure/2.0/forest/latest", json={"structureId": s_id}, headers=self.get_headers(), name="Read_06_Plugin_Structure")

    @task(2)
    def read_07_plugin_rich_filter(self):
        if not TEST_DATA.get("rich_filters"): return
        rf_id = random.choice(TEST_DATA["rich_filters"])
        self.client.get(f"/rest/rich-filters/1.0/filter?filterId={rf_id}", headers=self.get_headers(), name="Read_07_Plugin_RichFilter")

    @task(1)
    def read_08_plugin_plans(self):
        if not TEST_DATA.get("plans"): return
        p_id = random.choice(TEST_DATA["plans"])
        # UPDATED: Use the modern Roadmap API (GET instead of POST)
        self.client.get(f"/rest/roadmap/1.0/plans/{p_id}", headers=self.get_headers(), name="Read_08_Plugin_Portfolio")

    @task(1)
    def read_09_plugin_tempo(self):
        if not TEST_DATA.get("tempo_teams"): return
        t_id = random.choice(TEST_DATA["tempo_teams"])
        self.client.get(f"/rest/tempo-teams/2/team/{t_id}/member", headers=self.get_headers(), name="Read_09_Plugin_Tempo")

class JiraWriteUser(JiraBaseUser):
    def on_start(self):
        super().on_start()
        self.pending_rollbacks = {}
        self.my_created_issues = []

    @task(5)
    def write_01_edit_issue_description(self):
        if not TEST_DATA["issues"]: return
        issue_key = random.choice(TEST_DATA["issues"])
        headers = self.get_headers()
        r = self.client.get(f"/rest/api/2/issue/{issue_key}?fields=description", headers=headers, name="Write_01_Step1_Fetch_Desc")
        if r.status_code != 200: return
        try: original = r.json()["fields"].get("description", "")
        except: original = ""
        
        r_edit = self.client.put(f"/rest/api/2/issue/{issue_key}", json={"fields": {"description": f"{original}\n[LoadTest {uuid.uuid4()}]"}}, headers=headers, name="Write_02_Step2_Update_Desc")
        if r_edit.status_code == 204:
            self.pending_rollbacks[issue_key] = {"original": original, "time": time.time()}

    @task(5)
    def write_02_rollback_description(self):
        now = time.time()
        for key in list(self.pending_rollbacks.keys()):
            entry = self.pending_rollbacks[key]
            if now - entry["time"] > 30:
                self.client.put(f"/rest/api/2/issue/{key}", json={"fields": {"description": entry["original"]}}, headers=self.get_headers(), name="Write_03_Rollback_Desc")
                del self.pending_rollbacks[key]
                logger.info(f"ROLLBACK | {key} | Reverted")
                return

    @task(2)
    def write_03_create_issue(self):
        if not TEST_DATA.get("create_meta"): return
        meta = random.choice(TEST_DATA["create_meta"])
        payload = {"fields": {"project": {"key": meta["key"]}, "summary": f"LoadTest {uuid.uuid4()}", "issuetype": {"id": meta["issue_type_id"]}}}
        r = self.client.post("/rest/api/2/issue", json=payload, headers=self.get_headers(), name="Write_04_Create_Issue")
        if r.status_code == 201:
            key = r.json()["key"]
            self.my_created_issues.append(key)
            SHARED_CREATED_ISSUES.append(key)
            logger.info(f"CREATED | {key}")

    @task(2)
    def write_04_add_comment(self):
        if not TEST_DATA["issues"]: return
        target = random.choice(TEST_DATA["issues"])
        self.client.post(f"/rest/api/2/issue/{target}/comment", json={"body": "LoadTest"}, headers=self.get_headers(), name="Write_05_Add_Comment")

    @task(2)
    def write_99_cleanup_created_issues(self):
        if len(self.my_created_issues) > 400:
            key = self.my_created_issues.pop(0)
            self.client.delete(f"/rest/api/2/issue/{key}", headers=self.get_headers(), name="Write_99_Cleanup_Delete")
            if key in SHARED_CREATED_ISSUES: SHARED_CREATED_ISSUES.remove(key)

if FULL_CONFIG.get("test_mode") == "mixed":
    JiraReadUser.weight = RATIOS["read_weight"]
    JiraWriteUser.weight = RATIOS["write_weight"]
else:
    JiraReadUser.weight = 100; JiraWriteUser.weight = 0

class DynamicLoadShape(LoadTestShape):
    target_users = TARGET_USERS
    duration_sec = PROFILE_CONFIG["total_duration_minutes"] * 60
    ramp_up_sec = PROFILE_CONFIG["ramp_up_minutes"] * 60
    ramp_down_sec = PROFILE_CONFIG["ramp_down_minutes"] * 60
    spawn_rate = 2

    def tick(self):
        run_time = self.get_run_time()
        if run_time > self.duration_sec: return None
        if run_time < self.ramp_up_sec:
            current_target = int((run_time / self.ramp_up_sec) * self.target_users)
            return (max(1, current_target), self.spawn_rate)
        steady_end = self.duration_sec - self.ramp_down_sec
        if run_time < steady_end:
            return (self.target_users, self.spawn_rate)
        remaining_time = self.duration_sec - run_time
        current_target = int((remaining_time / self.ramp_down_sec) * self.target_users)
        return (max(1, current_target), self.spawn_rate)
