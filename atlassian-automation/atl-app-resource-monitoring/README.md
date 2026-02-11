# Jira App Resource Monitoring

Flask-based monitoring for Jira (and Confluence) application nodes: **always-on background collection** with time-series CSV per environment, Z-score heat map, trend/prediction arrows, **Apdex** from access logs, and a **view-only UI** with plots and CSV download.

## Features

- **Background collection:** When the app runs, it collects metrics for all configured environments (or a configurable list) every 60 seconds. No “start/stop” in the UI.
- **CSV on disk:** One file per environment: `data/monitoring_<env>.csv`. Rows are appended each tick. New columns (e.g. Apdex) are added via a one-time migration so existing files keep all history.
- **UI:** Choose environment → view latest snapshot, Z-score colors, trend arrows, and prediction. **Download CSV** for the selected env. **Plot:** click any metric to open a time-series chart (range 5 min–1 month, custom window, Actual or Z-Score). UI auto-refreshes every 60 seconds.
- **Apdex:** From access-log response times: satisfied &lt;2 s, neutral 2–5 s, not satisfied &gt;5 s. Score = (satisfied + 0.5×neutral) / total. Shown per app node with Z-score and trend; plottable.
- **Z-score and trend:** Numeric metrics are colored by anomaly (green / yellow / red) and show ↑/↓ (recent) and → (improve/worsen). Configurable in `config/default.yaml` under `monitoring.z_score`.

## Requirements

- Python 3.10+
- Passwordless SSH (key-based) to each app server as the configured user (e.g. `svcjira`)
- Servers: Linux with `ss` (or `netstat`), `free`, `ps`, `/proc/loadavg`, `/proc/stat`; access to Jira/Confluence logs for access-log and Apdex metrics

## Setup

```bash
cd atl-app-resource-monitoring-test
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

- **Default:** `config/default.yaml` — app port, SSH user, timeouts, paths, **monitoring** (see below).
- **Environments:** `config/environments/<name>.yaml` — e.g. `VMW-Jira.yaml`, `BIT-Jira.yaml`. Each has:
  - `environment`, `domain`, `servers` (short hostnames), `paths` (dbconfig, jira_home, setenv, access_log_dir, app_log_file), `ssh_user`, `app_port` (or `jira_app_port`).

**Monitoring (in `config/default.yaml`):**

- `csv_directory`: directory for CSV and latest snapshots (default `data`).
- `background_environments`: list of env names to collect (e.g. `[VMW-Jira, BIT-Jira]`). If **empty**, **all** environments under `config/environments/` are collected.
- `interval_seconds`: collection interval (default 60).
- `csv_window_minutes`: window for Z-score baseline in minutes (default **480** = 8 hours). Using 8 hours is recommended for shift-based anomaly detection (e.g. NASA/EMEA/APAC) so that prolonged outages (e.g. 30–60 min) do not dilute the baseline and keep showing as anomalies.
- `z_score`: `normal_max`, `medium_max`, `high_max` for green / yellow / red (defaults 1.75, 2.75, 2.75).

## Run

```bash
python run.py
```

Then open `http://localhost:9080` (or your configured port).

- **Environment** dropdown: select which environment to view.
- **Download CSV:** download the current env’s time-series CSV (all rows, with Z/trend/pred and Apdex columns when present).
- **Cards:** latest metrics per app/DB node; click a numeric metric to open the **plot** below (range, Actual/Z-Score, custom window, collapse).

**Important:** Use a **single worker** so only one process runs the background collector. For example:

```bash
gunicorn -w 1 -b 0.0.0.0:9080 "app.flask_app:create_app()"
```

If you use multiple workers, either run the collector in a separate process or use a distributed lock.

## Adding a new environment

1. Add `config/environments/<Name>.yaml` with `environment`, `domain`, `servers`, `paths`, `ssh_user`, app port.
2. (Optional) Add `<Name>` to `monitoring.background_environments` in `config/default.yaml` if you don’t want “all envs” collected.
3. Restart the app. The new env appears in the dropdown and is collected on the same interval.

## Deployment (e.g. corporate server)

1. Stop the app, tar the project (include the `data/` folder if you want to keep existing CSVs).
2. Copy the tar to the server, extract, then:
   ```bash
   pip install -r requirements.txt
   python run.py
   # or: gunicorn -w 1 -b 0.0.0.0:9080 "app.flask_app:create_app()"
   ```
3. Existing `data/monitoring_<env>.csv` files are kept; the app continues to append. New columns (e.g. Apdex) are added automatically on first append (migration: header extended, old rows get empty for new columns).
4. Expose the app URL; users open it, pick environment, view data, download CSV, and use plots as needed.

## CSV and Apdex

- **Columns:** timestamp plus per-node metrics (load, CPU, memory, heap, access log counts, response time percentiles, **apdex**, **apdex_satisfied**, **apdex_neutral**, **apdex_unsatisfied**), then for each base metric: `_z`, `_z_color`, `_trend`, `_pred`.
- **Apdex:** Computed from the same access-log lines used for response times. Satisfied &lt;2 s, neutral 2–5 s, not satisfied &gt;5 s; score = (satisfied + 0.5×neutral) / total. If you add Apdex to the code after already having CSVs, the first append for that env migrates the file (new columns, old rows blank for Apdex).

## How metrics are gathered

1. **SSH** to each node; read DB config, run `ss -tpn`, `free -m`, `/proc/loadavg`, `/proc/stat`, `ps`, and (for Jira/Confluence) access/app logs for the last 5 minutes.
2. **Access log:** Parsed for request count, unique users, response time percentiles (90/95/99/avg) and **Apdex** (satisfied/neutral/unsatisfied counts and score).
3. Results are flattened to one row per collect, Z-score and trend are computed from the last N minutes of CSV data, and the extended row is appended to `data/monitoring_<env>.csv` and the latest snapshot written to `data/latest_<env>.json` for the UI.
