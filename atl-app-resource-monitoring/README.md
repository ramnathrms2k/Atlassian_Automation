# Atlassian App Resource Monitoring

Flask-based monitoring for Jira and Confluence application nodes: **always-on background collection** with time-series CSV per environment, Z-score heat map, trend/prediction arrows, **Apdex** from access logs, **global access-log metrics** (unique users, percentiles), and a **view-only UI** with plots and CSV download.

## Features

- **Background collection:** When the app runs, it collects metrics for all configured environments (or a configurable list) every 60 seconds. No “start/stop” in the UI.
- **CSV on disk:** One file per environment: `data/monitoring_<env>.csv`. Rows are appended each tick. New columns (e.g. Apdex, global) are added via a one-time migration so existing files keep all history.
- **UI:** Choose environment → view latest snapshot, Z-score colors, trend arrows, and prediction. **Download CSV** for the selected env. **Plot:** click any metric to open a time-series chart (range 5 min–1 month, custom window, Actual or Z-Score). UI auto-refreshes every 60 seconds.
- **Apdex:** From access-log response times: satisfied <2 s, neutral 2–5 s, not satisfied >5 s. Score = (satisfied + 0.5×neutral) / total. Shown per app node and **global (all nodes)** with Z-score and trend; plottable.
- **Global access log (5m):** Cumulative request count, **true unique users** (union across nodes), and request-weighted 99p/95p/90p/avg response times.
- **Z-score and trend:** Numeric metrics are colored by anomaly (green / yellow / red) and show ↑/↓ (recent) and → (improve/worsen). Configurable in `config/default.yaml` under `monitoring.z_score`.
- **SSH retry:** Transient connection errors (e.g. after VPN reconnect) trigger up to 3 attempts with a 2s delay.

## Requirements

- Python 3.10+
- Passwordless SSH (key-based) to each app server as the configured user. Replace `TOKEN` in config with your SSH user.
- Servers: Linux with `ss` (or `netstat`), `free`, `ps`, `/proc/loadavg`, `/proc/stat`; access to Jira/Confluence logs for access-log and Apdex metrics.

## Setup

```bash
cd atl-app-resource-monitoring
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

- **Default:** `config/default.yaml` — app port, SSH user (`TOKEN` → replace), timeouts, paths, **monitoring** (see below).
- **Environments:** `config/environments/<name>.yaml` — replace placeholder hostnames (`jira-app-01`, etc.) and `domain` (`.example.com`) with your servers and domain. Each file has:
  - `environment`, `domain`, `servers` (short hostnames), `paths` (dbconfig, jira_home, setenv, access_log_dir, app_log_file), `ssh_user` (`TOKEN` → replace), `app_port` (or `jira_app_port`).

**Monitoring (in `config/default.yaml`):**

- `csv_directory`: directory for CSV and latest snapshots (default `data`).
- `background_environments`: list of env names to collect (e.g. `[VMW-Jira, BIT-Jira]`). If **empty**, **all** environments under `config/environments/` are collected.
- `interval_seconds`: collection interval (default 60).
- `csv_window_minutes`: window for Z-score (default 60).
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

1. Add `config/environments/<Name>.yaml` with `environment`, `domain`, `servers`, `paths`, `ssh_user`, app port. Use existing env files as templates; replace `TOKEN` and placeholder hostnames.
2. (Optional) Add `<Name>` to `monitoring.background_environments` in `config/default.yaml` if you don’t want “all envs” collected.
3. Restart the app. The new env appears in the dropdown and is collected on the same interval.

## Deployment (e.g. corporate server)

1. Stop the app, tar the project (include the `data/` folder if you want to keep existing CSVs). Exclude `venv`, `__pycache__`, `.pytest_cache`.
2. Copy the tar to the server, extract, then:
   ```bash
   pip install -r requirements.txt
   # Set monitoring.background_environments in config/default.yaml if needed
   python run.py
   # or: gunicorn -w 1 -b 0.0.0.0:9080 "app.flask_app:create_app()"
   # or: screen -S monitoring then run the above; detach with Ctrl+A D
   ```
3. Existing `data/monitoring_<env>.csv` files are kept; the app continues to append. New columns (e.g. Apdex) are added automatically on first append (migration: header extended, old rows get empty for new columns).
4. Expose the app URL; users open it, pick environment, view data, download CSV, and use plots as needed.

## Storage and growth

- Only **CSV files** grow; `data/latest_<env>.json` is overwritten each run (~15–35 KB per env). No app log files by default.
- At 60s interval: ~2.5 KB per row, **~24 MB per environment per week**, **~101 MB per environment per month**. See `docs/STORAGE_GROWTH.md` for cleanup/archive suggestions.

## CSV and Apdex

- **Columns:** timestamp plus per-node metrics (load, CPU, memory, heap, access log counts, response time percentiles, **apdex**, **apdex_satisfied**, **apdex_neutral**, **apdex_unsatisfied**), global access-log metrics, then for each base metric: `_z`, `_z_color`, `_trend`, `_pred`.
- **Apdex:** Computed from the same access-log lines used for response times. Satisfied <2 s, neutral 2–5 s, not satisfied >5 s; score = (satisfied + 0.5×neutral) / total.

## How metrics are gathered

1. **SSH** to each node (with retry on transient failures); read DB config, run `ss -tpn`, `free -m`, `/proc/loadavg`, `/proc/stat`, `ps`, and (for Jira/Confluence) access/app logs for the last 5 minutes.
2. **Access log:** Parsed for request count, unique users, response time percentiles (90/95/99/avg) and **Apdex** (satisfied/neutral/unsatisfied counts and score). Global aggregates: union of unique users, request-weighted percentiles.
3. Results are flattened to one row per collect, Z-score and trend are computed from the last N minutes of CSV data, and the extended row is appended to `data/monitoring_<env>.csv` and the latest snapshot written to `data/latest_<env>.json` for the UI.

## Tests

```bash
python -m pytest tests/ -v
```
