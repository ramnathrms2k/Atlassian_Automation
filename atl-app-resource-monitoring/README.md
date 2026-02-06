# Atlassian App Resource Monitoring

## Overview

A Flask-based web dashboard for monitoring Jira and Confluence Data Center application nodes: incoming connections, database connections (with PIDs), system resources (CPU, load average, memory), and JVM heap. Supports **on-demand** refresh and **monitoring** mode with configurable interval. Supports multiple environments (Jira and Confluence) from a single dropdown.

## What It Does

- **Multi-Environment**: Switch between Jira and Confluence (and multiple envs) from one UI; all environments listed in a single dropdown
- **App Node Monitoring**: Per-node metrics: load average, CPU %, memory (used/available), swap, JVM heap/non-heap, incoming connections to app port, DB connection count with PIDs
- **DB Node Monitoring**: Unique DB hosts from app configs; SSH to DB nodes for load, CPU, memory, swap, and connection counts
- **Jira & Confluence**: Jira uses `dbconfig.xml` for DB; Confluence uses `server.xml` (JDBC resource); version from `pom.properties` for each app type
- **Real-Time Updates**: On-demand refresh or auto-refresh at configurable interval (default 60 seconds)

## Prerequisites

- **Python**: 3.10 or higher
- **SSH**: Passwordless (key-based) SSH to each app server and (optionally) DB server as the configured user (e.g. `svcjira`)
- **Target nodes**: Linux with `ss` (or `netstat`), `free`, `ps`, `/proc/loadavg`, `/proc/stat`

## Configuration

- **Default config:** `config/default.yaml` — app port (>9000), refresh interval, SSH user, timeouts, default paths
- **Environment config:** `config/environments/<env>.yaml` — server list, domain, paths, app type (jira/confluence), app port

Example environments (generic; replace hostnames and domain with your values):

- **Example-Jira**: `jira-app-01`, `jira-app-02`, `jira-app-03`; domain `.example.com`; paths for Jira home, dbconfig, setenv; app port 8080
- **Example-Confluence**: `conf-app-01`–`03`; setenv and `server_xml` path; app port 8090
- **Example-BIT-Jira**: Same pattern for a second Jira cluster

To add your environment:

1. Copy an example YAML under `config/environments/` and rename (e.g. `My-Jira.yaml`)
2. Set `environment`, `domain`, `servers`, `paths`, `ssh_user`, `app_port`; for Confluence set `app_type: confluence` and `paths.server_xml`
3. Run with `JIRA_MONITOR_ENV=My-Jira` or select from the UI dropdown

**Important**: Replace example server hostnames and domain with your actual values. Credentials are not stored in config; SSH key-based auth is required.

## How to Use

### Setup

```bash
cd atl-app-resource-monitoring
python3 -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Run

```bash
python run.py
```

Then open `http://localhost:9080` (or the port set in `config/default.yaml` or `JIRA_MONITOR_PORT`). Use the **Environment** dropdown to select an environment, **Refresh once** to fetch metrics, or **Start monitoring** for auto-refresh.

### Optional

- Override app port (must be >9000): `export JIRA_MONITOR_PORT=9080`
- Default environment: `export JIRA_MONITOR_ENV=Example-Jira`

## How Metrics Are Gathered

1. **SSH** to each app node as the configured user
2. **DB host/port**: Jira — read `dbconfig.xml` and parse JDBC URL; Confluence — read `server.xml` and parse `jdbc/confluence` Resource URL
3. **Connections**: `ss -tpn` (fallback `netstat -tpn`); count incoming to app port and outgoing to DB; collect PIDs
4. **Memory**: `free -m`
5. **Load**: `cat /proc/loadavg`
6. **CPU**: Two samples of `/proc/stat` 1 second apart
7. **Version**: Jira — `atlassian-jira/.../jira-webapp-dist/pom.properties`; Confluence — `confluence/.../confluence-webapp/pom.properties`
8. **DB nodes**: Unique (host, port) from all app nodes; SSH to each DB host for system and connection metrics

## Tests

```bash
python -m pytest tests/ -v
```

## Documentation

- **Purpose**: Resource and connection monitoring for Jira and Confluence Data Center clusters
- **Use Cases**: Capacity monitoring, connection troubleshooting, health overview, multi-environment visibility
- **Documentation**: This README

---

**Note**: This is production-ready code. Configure environment YAMLs with your server hostnames and domain; ensure SSH key-based access to app (and optionally DB) nodes.
