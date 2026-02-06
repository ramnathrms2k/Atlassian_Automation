# Atlassian App Resource Monitoring

## Overview

Flask-based web dashboard for monitoring Jira and Confluence Data Center application nodes: incoming connections, database connections (with PIDs), system resources (CPU, load average, memory), JVM heap, and **log-based metrics** (access and app logs, last 5 minutes). Supports multiple environments from a single dropdown, with on-demand refresh and monitoring mode.

## What It Does

- **Multi-Environment**: Switch between Jira and Confluence (and multiple envs) from one UI; all environments in a single dropdown
- **App Node Monitoring**: Per-node metrics: load average, CPU %, memory (used/available), swap, JVM heap/non-heap, incoming connections to app port, DB connection count with PIDs
- **Access Log (5m)**: Per node — unique users, request count, and response time percentiles (99p, 95p, 90p, avg in seconds) from Tomcat access logs
- **App Log (5m)**: Per node — unique threads and line count from application logs (atlassian-jira.log / atlassian-confluence.log) in the last 5 minutes
- **DB Node Monitoring**: Unique DB hosts from app configs; SSH to DB nodes for load, CPU, memory, swap, and connection counts
- **Jira & Confluence**: Jira uses `dbconfig.xml` for DB; Confluence uses `server.xml` (JDBC resource); version from `pom.properties` for each app type
- **Real-Time Updates**: On-demand refresh or auto-refresh at configurable interval (default 60 seconds)

## Prerequisites

- **Python**: 3.10 or higher
- **SSH**: Passwordless (key-based) SSH to each app server and (optionally) DB server as the configured user (e.g. `svcjira`)
- **Target nodes**: Linux with `ss` (or `netstat`), `free`, `ps`, `/proc/loadavg`, `/proc/stat`

## Configuration

- **Default config:** `config/default.yaml` — app port (>9000), refresh interval, SSH user, timeouts, default paths, log paths
- **Environment config:** `config/environments/<env>.yaml` — server list, domain, paths (setenv, dbconfig or server_xml, access_log_dir, app_log_file), app type (jira/confluence), app port

To add your environment: add a YAML under `config/environments/` with `environment`, `domain`, `servers`, `paths`, `ssh_user`, `app_port`; for Confluence set `app_type: confluence` and `paths.server_xml`. Run with `JIRA_MONITOR_ENV=<name>` or select from the UI dropdown.

## How to Use

```bash
cd atl-app-resource-monitoring
python3 -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python run.py
```

Open `http://localhost:9080` (or `JIRA_MONITOR_PORT`). Use the **Environment** dropdown, **Refresh once**, or **Start monitoring**.

## How Metrics Are Gathered

1. **SSH** to each app node as the configured user
2. **DB host/port**: Jira — `dbconfig.xml`; Confluence — `server.xml` (jdbc/confluence Resource URL)
3. **Connections**: `ss -tpn`; count incoming to app port and outgoing to DB; collect PIDs
4. **Memory, load, CPU**: `free -m`, `/proc/loadavg`, two samples of `/proc/stat`
5. **Version**: from pom.properties (Jira vs Confluence paths)
6. **Access log (5m)**: Tail access log (Jira: install logs; Confluence: conf_access_log), parse timestamp and user; extract response time (Jira: status bytes time_ms; Confluence: status Nms bytes); compute 99p, 95p, 90p, avg in seconds
7. **App log (5m)**: Tail atlassian-jira.log / atlassian-confluence.log, parse timestamp and thread; count unique threads and lines in last 5 minutes (server timezone used when log has no TZ)
8. **DB nodes**: Unique (host, port) from app configs; SSH to each DB host for system and connection metrics

## Tests

```bash
python -m pytest tests/ -v
```

## Documentation

- **Purpose**: Resource, connection, and log-based monitoring for Jira and Confluence Data Center clusters
- **Use Cases**: Capacity monitoring, connection troubleshooting, response time and concurrency visibility, multi-environment health overview
- **Documentation**: This README
