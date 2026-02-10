# Response Time Analysis

Analyze Jira/Confluence (or any Tomcat) access logs by **user** and/or **URI** over a time range. Produces CSV with timestamp, user, URI (path without query params), response time (ms), and **Z-score** for anomaly detection. Flask UI on **port 9090** with:

- **On-demand mode**: Pick product, nodes, date range (or last N days), filters → run analysis → view table + response time & Z-score charts, download CSV. Option to view per-node or cumulative (all nodes sorted by time with node column).
- **Live mode**: Tail access logs in real time with the same filters; table and charts update as new lines arrive.

## Config

All settings are in **`config/config.yaml`**:

- **SSH**: `ssh_user`, `ssh_timeout_seconds`, `ssh_options`
- **Products**: `products.<id>` with `display_name`, `domain`, `nodes[]` (each node: `name`, `hostname`, `log_path`, `log_file_pattern`, `server_xml_path`)
- **Log pattern**: `log_pattern_type` (e.g. `common_with_D` for Tomcat `%h %l %u %t "%r" %s %b %D`)
- **Flask**: `flask_port` (default 9090), `default_days`, `default_z_threshold`

Example nodes (from your setup):

- **Jira**: `jira-lvnv-it-101`–`103` (`.lvn.broadcom.net`), logs under `/export/jira/logs`, file `access_log.%Y-%m-%d`
- **Confluence**: `conf-lvnv-it-101`–`103`, logs under `/export/confluence/logs`, file `conf_access_log.%Y-%m-%d.log`

Passwordless SSH as `svcjira` to these hosts is required from the machine running the app.

## Run

```bash
cd /path/to/response-time-analysis
pip install -r requirements.txt
python app.py
```

Open **http://localhost:9090**.

## Usage

1. **On-demand**
   - Choose product (e.g. VMW-Jira), optionally restrict nodes (or leave empty = all).
   - Set **From/To** dates or **Last N days**.
   - Optionally filter by **User** (substring) and/or **URI** (substring).
   - Scope: **Cumulative** (single table sorted by time, with node column) or **Per-node**.
   - Click **Run analysis**. Table shows timestamp, node (if cumulative), user, uri, response_time_ms, z_score. Two charts: response time and Z-score over time. **Download CSV** saves the same data.

2. **Live**
   - Choose product and nodes, optional user/URI filters.
   - Click **Start live tail**. Table and charts refresh every 2s with new lines. **Stop** ends the session.

## Log format

Parser expects Tomcat-style access lines with **response time in ms** at the end (e.g. `%D` in `pattern`). Format: `%h %l %u %t "%r" %s %b %D`. URI is stored without query parameters for grouping. Z-score is computed over the selected series for anomaly detection (e.g. |z| > 2).
