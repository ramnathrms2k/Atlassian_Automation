# Atlassian Automation Frameworks

## Overview

This folder contains automation frameworks, scripts, and tools for managing, monitoring, and maintaining Atlassian Jira and Confluence Data Center environments.

## Repository Structure

This folder contains **20 specialized automation frameworks**, each designed for specific operational use cases. Key frameworks include:

### Log Analysis & Monitoring
- **[atl-app-resource-monitoring](atl-app-resource-monitoring/)** - Flask-based monitoring for Jira and Confluence app nodes: always-on background collection, time-series CSV per environment, Z-score heat map, trend/prediction arrows, Apdex and global access-log metrics (5m), view-only UI with plots and CSV download; multi-environment dropdown
- **[response-time-analysis](response-time-analysis/)** - Analyze Jira/Confluence access logs by user and URI over a date range; on-demand and live-tail modes, CSV export with response time and anomaly (Z) score, Flask UI on port 9090

### Other frameworks
- **jira_load_test_framework**, **vrli_framework**, **vrli_poc**, **jira_logparser**, **jira-health-dashboard**, **comprehensive-jira-health-dashboard**, **jira-response-time-tracker**, **response-time-analysis**, **jira_preflight_validator**, **jira_validator**, **atl-binary-compare**, **jira-project-config-audit**, **jira_cf_audit**, **atlassian_plugin_report**, **user_audit**, **fetch_groups**, **sar_plotter**, **atlassian_uploader**, **psirt_mailhandler**

See the [repository root README](../README.md) for the full list, descriptions, and documentation links.

## Quick Start

1. Browse the framework list in the root README.
2. Open the framework folder (e.g. `atl-app-resource-monitoring/`) and read its README.
3. Replace `TOKEN` placeholders in config, then follow the framework's setup and run instructions.
