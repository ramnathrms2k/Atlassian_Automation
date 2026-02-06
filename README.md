# Atlassian Automation Frameworks

## Overview

This repository contains a comprehensive collection of automation frameworks, scripts, and tools for managing, monitoring, and maintaining Atlassian Jira and Confluence Data Center environments. These production-ready frameworks support various operational tasks including performance testing, log analysis, validation, auditing, and integration workflows.

## Repository Structure

This folder contains **19 specialized automation frameworks**, each designed for specific operational use cases:

### Performance & Load Testing
- **[jira_load_test_framework](jira_load_test_framework/)** - Comprehensive load testing framework using Locust for performance certification, resiliency, and longevity testing

### Log Analysis & Monitoring
- **[vrli_framework](vrli_framework/)** - Hybrid log extraction framework for VMware Aria Operations for Logs (vRLI) with automated field discovery
- **[vrli_poc](vrli_poc/)** - Proof of concept scripts for vRLI log fetching, analysis, and statistics generation
- **[jira_logparser](jira_logparser/)** - Comprehensive log analysis framework for Jira access logs and application logs
- **[atl-app-resource-monitoring](atl-app-resource-monitoring/)** - Flask-based web dashboard for monitoring Jira and Confluence app nodes: connections, DB connections, system and JVM metrics; multi-environment dropdown
- **[jira-health-dashboard](jira-health-dashboard/)** - Flask-based web dashboard for monitoring health and index status of multiple Jira Data Center servers
- **[comprehensive-jira-health-dashboard](comprehensive-jira-health-dashboard/)** - Comprehensive real-time health monitoring dashboard for Jira Data Center clusters with system metrics, database monitoring, and dual disk usage tracking
- **[jira-response-time-tracker](jira-response-time-tracker/)** - Flask-based web interface for monitoring slow requests from Jira access logs, grouped by user ID with statistics on count, maximum time, and timestamps

### Validation & Preflight
- **[jira_preflight_validator](jira_preflight_validator/)** - Pre-deployment validation framework for Jira Data Center nodes
- **[jira_validator](jira_validator/)** - Binary and configuration validation framework for Jira installations
- **[atl-binary-compare](atl-binary-compare/)** - Utility for comparing setenv.sh configuration files between different versions of Jira or Confluence

### Auditing & Reporting
- **[jira-project-config-audit](jira-project-config-audit/)** - Project configuration audit (workflow scheme, automation rules, permissions, screens, ScriptRunner behaviours) with web UI and side-by-side compare
- **[jira_cf_audit](jira_cf_audit/)** - Custom field audit framework for identifying usage, empty fields, and stale candidates
- **[atlassian_plugin_report](atlassian_plugin_report/)** - Plugin and marketplace app auditing framework for license compliance and cost analysis
- **[user_audit](user_audit/)** - User auditing framework for identifying active licensed users, departments, and last login information for license optimization

### System Management
- **[fetch_groups](fetch_groups/)** - LDAP group fetching and analysis framework for Atlassian-related groups
- **[sar_plotter](sar_plotter/)** - SAR (System Activity Reporter) data plotting and visualization framework

### Integration & Utilities
- **[atlassian_uploader](atlassian_uploader/)** - Utility for uploading large files to Atlassian Premier Support tickets
- **[psirt_mailhandler](psirt_mailhandler/)** - Groovy script for JSM email handler to process PSIRT notifications

## Quick Start

### For New Users

1. **Browse Frameworks**: Review the framework list above and identify which tools meet your needs
2. **Read Framework README**: Each framework has a detailed README with prerequisites, configuration, and usage instructions
3. **Check Prerequisites**: Verify connectivity, credentials, and software requirements before execution
4. **Configure**: Update configuration files with your environment details (servers, credentials, thresholds)
5. **Execute**: Follow the usage instructions in each framework's README

### Common Prerequisites Across Frameworks

Most frameworks require:
- **Python 3.7+** (for Python-based frameworks)
- **Bash Shell** (for shell script-based frameworks)
- **Network Access** to target systems (Jira, Confluence, databases, LDAP, vRLI)
- **Credentials/Tokens** (API tokens, database credentials, SSH keys)
- **Appropriate Permissions** (read/write access as required)

**Important**: All credentials and tokens in configuration files have been sanitized (replaced with "TOKEN" placeholder). Replace these with actual values before execution.

## Framework Details

### Performance & Load Testing

#### jira_load_test_framework
- **Purpose**: Performance testing and certification for Jira Data Center
- **Key Features**: Resiliency and longevity profiles, infrastructure monitoring, automated reporting
- **Use Cases**: Performance certification, capacity planning, stress testing
- **Documentation**: [README](jira_load_test_framework/README.md)

### Log Analysis & Monitoring

#### vrli_framework
- **Purpose**: Advanced log extraction and querying from vRLI
- **Key Features**: Hybrid extraction (server-side + client-side), automated field discovery, numeric filtering
- **Use Cases**: Performance incident analysis, user forensics, log analytics
- **Documentation**: [README](vrli_framework/README.md)

#### vrli_poc
- **Purpose**: Proof of concept scripts for vRLI integration
- **Key Features**: Log fetching, field discovery, statistics generation
- **Use Cases**: Testing vRLI integration patterns, log analysis workflows
- **Documentation**: [README](vrli_poc/README.md)

#### jira_logparser
- **Purpose**: Comprehensive Jira log analysis and monitoring
- **Key Features**: User activity analysis, performance monitoring, system analytics, diagnostic bundles
- **Use Cases**: Performance monitoring, user behavior analysis, system health monitoring
- **Documentation**: [README](jira_logparser/README.md)

#### atl-app-resource-monitoring
- **Purpose**: Resource and connection monitoring for Jira and Confluence Data Center application and DB nodes
- **Key Features**: Multi-environment dropdown (Jira/Confluence), per-node metrics (load, CPU, memory, JVM heap), incoming and DB connection counts with PIDs, DB node metrics, on-demand and auto-refresh
- **Use Cases**: Capacity monitoring, connection troubleshooting, cluster health overview, multi-environment visibility
- **Documentation**: [README](atl-app-resource-monitoring/README.md)

#### jira-health-dashboard
- **Purpose**: Real-time health monitoring dashboard for Jira Data Center clusters
- **Key Features**: Multi-server monitoring, index health checks, response time tracking, web-based visualization
- **Use Cases**: Cluster health monitoring, index synchronization tracking, performance monitoring
- **Documentation**: [README](jira-health-dashboard/README.md)

#### comprehensive-jira-health-dashboard
- **Purpose**: Comprehensive real-time health monitoring dashboard for Jira Data Center clusters
- **Key Features**: 
  - Jira index health monitoring (DB count, index count, archive count)
  - System metrics (CPU, memory, swap, load average, disk usage)
  - Dual disk usage tracking (local + shared home for app nodes, local + binlogs for DB)
  - Database connection monitoring (per app node and total)
  - Database server metrics (connections, active queries, slow queries)
  - Auto-refresh functionality with configurable intervals
  - Color-coded alerts based on configurable thresholds
  - JSON API endpoint for programmatic access
- **Use Cases**: Comprehensive cluster health monitoring, database connection tracking, system resource monitoring, proactive alerting
- **Documentation**: [README](comprehensive-jira-health-dashboard/README.md)

#### jira-response-time-tracker
- **Purpose**: Monitor slow requests from Jira access logs across multiple servers
- **Key Features**: 
  - Access log analysis for slow requests (configurable threshold)
  - User-based statistics (count, max time, last time, timestamps)
  - Multi-server monitoring with separate scrollable boxes
  - Real-time updates via on-demand refresh
  - Configurable log paths, date formats, and analysis parameters
  - Scrollable tables for handling large datasets
  - JSON API endpoint for programmatic access
- **Use Cases**: Performance monitoring, identifying slow requests by user, troubleshooting performance issues, user behavior analysis
- **Documentation**: [README](jira-response-time-tracker/README.md)

### Validation & Preflight

#### jira_preflight_validator
- **Purpose**: Pre-deployment validation for Jira Data Center nodes
- **Key Features**: Multi-server validation, installation verification, database connectivity testing
- **Use Cases**: Pre-upgrade validation, deployment verification, configuration validation
- **Documentation**: [README](jira_preflight_validator/README.md)

#### jira_validator
- **Purpose**: Binary and configuration validation for Jira installations
- **Key Features**: Version checking, file integrity validation, configuration validation
- **Use Cases**: Installation verification, configuration compliance checking
- **Documentation**: [README](jira_validator/README.md)

#### atl-binary-compare
- **Purpose**: Compare setenv.sh configuration files between different versions
- **Key Features**: Automated download, selective extraction, unified diff comparison, migration guidance
- **Use Cases**: Version upgrade planning, configuration migration, change detection
- **Documentation**: [README](atl-binary-compare/README.md)

### Auditing & Reporting

#### jira_cf_audit
- **Purpose**: Custom field usage analysis and cleanup
- **Key Features**: Usage analysis, empty field detection, stale field identification
- **Use Cases**: Custom field optimization, cleanup planning, usage reporting
- **Documentation**: [README](jira_cf_audit/README.md)

#### atlassian_plugin_report
- **Purpose**: Plugin and marketplace app auditing
- **Key Features**: Plugin discovery, marketplace integration, license reporting, cost analysis
- **Use Cases**: License compliance, cost optimization, plugin inventory
- **Documentation**: [README](atlassian_plugin_report/README.md)

#### user_audit
- **Purpose**: User auditing and license optimization for Jira and Confluence
- **Key Features**: Active user identification, HR database integration, last login analysis, ghost license detection
- **Use Cases**: License optimization, compliance auditing, inactive user identification, ghost license reclamation
- **Documentation**: [README](user_audit/README.md)

#### jira-project-config-audit
- **Purpose**: Full project configuration audit from Jira database and optional ScriptRunner API
- **Key Features**: Workflow scheme details (steps, transitions, conditions, validators, post-functions), automation rules with owner/actor display names, permission details with user display names, screens and fields, ScriptRunner behaviours; Flask web UI; side-by-side compare for two audits
- **Use Cases**: Project config documentation, SBX vs PRD comparison, workflow and automation inventory, permission and screen auditing
- **Documentation**: [README](jira-project-config-audit/README.md)

### System Management

#### fetch_groups
- **Purpose**: LDAP group fetching and analysis for Atlassian groups
- **Key Features**: Group discovery, member analysis, audit reporting, bucket analysis
- **Use Cases**: Access management, group auditing, compliance reporting
- **Documentation**: [README](fetch_groups/README.md)

#### sar_plotter
- **Purpose**: System performance visualization from SAR data
- **Key Features**: Remote SAR analysis, historical analysis, performance metrics visualization
- **Use Cases**: Performance trend analysis, capacity planning, system monitoring
- **Documentation**: [README](sar_plotter/README.md)

### Integration & Utilities

#### atlassian_uploader
- **Purpose**: Large file upload utility for Premier Support tickets
- **Key Features**: File chunking, automated upload, progress tracking
- **Use Cases**: Uploading diagnostic bundles, log files to support tickets
- **Documentation**: [README](atlassian_uploader/README.md)

#### psirt_mailhandler
- **Purpose**: Automated PSIRT email processing for JSM
- **Key Features**: Email processing, issue creation/updates, workflow integration
- **Use Cases**: Automated PSIRT ticket creation from email notifications
- **Documentation**: [README](psirt_mailhandler/README.md)

## Security & Best Practices

### Credential Management
- **All tokens and passwords are sanitized** - Replace "TOKEN" placeholders with actual values
- **Never commit credentials** - Use environment variables or secure vaults in production
- **Use read-only credentials** - Where possible, use read-only database users and API tokens
- **Rotate credentials periodically** - Follow your organization's credential rotation policies

### Code Standards
- **Production-Ready**: All code is production-ready and currently in use
- **No Sensitive Data**: All sensitive information has been sanitized before commit
- **Comprehensive Documentation**: Each framework includes detailed README with prerequisites and usage
- **Error Handling**: Scripts include error handling and validation

### Maintenance
- **Version Control**: All code is version controlled in Git
- **Documentation**: README files are maintained and updated with each change
- **Testing**: Code has been tested in production environments
- **Support**: Refer to individual framework READMEs for troubleshooting

## Getting Help

### For Each Framework
1. **Read the README**: Each framework has a comprehensive README with:
   - Overview and purpose
   - Prerequisites and requirements
   - Configuration instructions
   - Usage examples
   - Troubleshooting guides

2. **Check Prerequisites**: Verify all prerequisites are met before execution

3. **Review Configuration**: Ensure configuration files are properly set up

4. **Test Connectivity**: Use provided test commands to verify connectivity

### Common Issues
- **Connectivity Problems**: Check network access, firewall rules, and credentials
- **Permission Errors**: Verify file permissions and user access rights
- **Missing Dependencies**: Install required Python packages or system tools
- **Configuration Errors**: Review configuration files and ensure all placeholders are replaced

## Contributing

### Adding New Frameworks
1. Create a new folder with descriptive name
2. Add all framework files
3. Create comprehensive README.md following the standard format
4. Sanitize all credentials/tokens (replace with "TOKEN")
5. Test thoroughly before committing

### Updating Existing Frameworks
1. Make code changes
2. Update README if functionality changes
3. Sanitize any new credentials
4. Test changes
5. Commit with descriptive message

### Documentation Standards
- Include comprehensive prerequisites section
- Document all configuration options
- Provide usage examples
- Include troubleshooting section
- Maintain consistency with other framework READMEs

## File Organization

```
atlassian-automation/
├── README.md                          # This file - overview of all frameworks
├── .gitignore                         # Git ignore rules for common files
├── jira_load_test_framework/         # Load testing framework
├── vrli_framework/                    # vRLI log extraction framework
├── vrli_poc/                          # vRLI proof of concept scripts
├── jira_logparser/                    # Jira log analysis framework
├── atl-app-resource-monitoring/       # Jira & Confluence app/DB resource and connection monitoring
├── jira-health-dashboard/             # Jira health monitoring dashboard
├── comprehensive-jira-health-dashboard/ # Comprehensive Jira health monitoring dashboard
├── jira-response-time-tracker/        # Jira response time tracking dashboard
├── jira_preflight_validator/          # Pre-deployment validation
├── jira_validator/                    # Binary/configuration validation
├── atl-binary-compare/                # Binary configuration comparison utility
├── jira-project-config-audit/         # Project config audit (workflow, automation, permissions, UI, compare)
├── jira_cf_audit/                     # Custom field auditing
├── atlassian_plugin_report/           # Plugin auditing and reporting
├── fetch_groups/                      # LDAP group management
├── sar_plotter/                       # System performance visualization
├── atlassian_uploader/                # File upload utility
├── psirt_mailhandler/                 # PSIRT email handler
└── user_audit/                        # User auditing framework
```

## Version Information

- **Repository**: GTO/Devops
- **Branch**: Atlassian_automation
- **Last Updated**: January 2025
- **Status**: Production-Ready
- **Maintainer**: GTO DevOps Team

## License & Usage

These frameworks are internal tools for Broadcom GTO DevOps team. All code is production-ready and currently in use for managing Atlassian environments.

---

**Note**: This is a collection of production-ready automation frameworks. Ensure all prerequisites are met and credentials are configured before execution. Refer to individual framework READMEs for detailed instructions.

