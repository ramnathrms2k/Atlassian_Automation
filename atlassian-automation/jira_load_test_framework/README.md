# Jira Load Test Framework

## Overview

A comprehensive load testing framework for Atlassian Jira Data Center using Locust. This framework performs performance testing with resiliency and longevity profiles, including infrastructure monitoring, resource discovery, and automated reporting.

## What It Does

- **Load Testing**: Simulates realistic user workloads (read/write operations) against Jira instances
- **Resource Discovery**: Automatically discovers issues, boards, dashboards, and other Jira resources
- **Infrastructure Monitoring**: Tracks CPU, memory, and load metrics during test execution
- **Performance Profiles**: Supports resiliency (2-hour) and longevity (6-hour) test profiles
- **Automated Reporting**: Generates HTML reports, CSV metrics, and visualization graphs

## Prerequisites

- Python 3.7+
- Locust framework: `pip install locust`
- Access to Jira instance(s) with API tokens
- SSH access to application nodes for monitoring (optional)

## Configuration

### Main Configuration File: `config.json`

Edit `config.json` to configure:

#### Environments
```json
{
  "environments": {
    "dev": {
      "base_url": "https://your-jira-instance.com",
      "tokens": ["TOKEN", "TOKEN"],
      "limits": {
        "resiliency": 160,
        "longevity": 100
      }
    }
  }
}
```

**Configuration Parameters:**
- `base_url`: Jira instance URL
- `tokens`: Array of Jira API tokens (Personal Access Tokens)
  - **Replace "TOKEN" with actual tokens** from Jira → Account Settings → Security → API Tokens
- `limits`: Maximum concurrent users for each profile

#### Test Profiles
```json
{
  "profiles": {
    "resiliency": {
      "total_duration_minutes": 120,
      "ramp_up_minutes": 20,
      "ramp_down_minutes": 20,
      "discovery_params": {
        "max_issues": 2000,
        "max_boards": 50,
        "max_filters": 50
      }
    }
  }
}
```

**Profile Parameters:**
- `total_duration_minutes`: Total test duration
- `ramp_up_minutes`: Time to reach target user count
- `ramp_down_minutes`: Time to reduce user count
- `discovery_params`: Limits for resource discovery

#### Read/Write Ratios
```json
{
  "ratios": {
    "read_weight": 85,
    "write_weight": 15
  }
}
```

**Ratio Parameters:**
- `read_weight`: Percentage of read operations (viewing issues, boards, etc.)
- `write_weight`: Percentage of write operations (creating/editing issues)

### Server Names and Locations

- **Server Configuration**: Edit `monitor.py` to configure target servers for infrastructure monitoring
- **SSH Access**: Ensure SSH access to application nodes if using infrastructure monitoring

### Thresholds

- **User Limits**: Configured in `config.json` under `environments[env]["limits"]`
- **Discovery Limits**: Configured in `profiles[profile]["discovery_params"]`
- **Performance Thresholds**: Review Locust HTML report for response time thresholds

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install locust requests

# Configure tokens in config.json
# Replace "TOKEN" placeholders with actual Jira API tokens
```

### 2. Run a Test

```bash
# Basic usage
./run_test.sh <environment> <profile>

# Examples
./run_test.sh dev resiliency
./run_test.sh dev longevity
```

### 3. Test Execution Flow

1. **Discovery Phase**: Discovers Jira resources (issues, boards, dashboards)
2. **Monitoring Start**: Begins infrastructure monitoring (if configured)
3. **Load Test**: Executes Locust load test with specified profile
4. **Monitoring Stop**: Stops infrastructure monitoring
5. **Report Generation**: Creates HTML report and graphs
6. **Archive**: Compresses all results into a single tar.gz file

### 4. Output Files

After execution, you'll find:
- `results_<RUN_ID>.tar.gz`: Complete results archive
- `report_<RUN_ID>.html`: Locust HTML report
- `metrics_<RUN_ID>.csv`: Infrastructure metrics
- `data_<RUN_ID>.json`: Discovered resources
- `execution_<RUN_ID>.log`: Execution log

## Credentials/Tokens

### Getting Jira API Tokens

1. Log into Jira
2. Go to: **Account Settings → Security → API Tokens**
3. Click **Create API Token**
4. Copy the token and add it to `config.json` in the `tokens` array

**Important**: Replace all "TOKEN" placeholders in `config.json` with actual tokens before running tests.

### Security Notes

- **Never commit tokens to version control**
- Use environment variables or secure vaults in production
- Rotate tokens periodically
- Use separate tokens for different environments

## Debug Scripts

The framework includes debug scripts for troubleshooting:

- `debug_create.py`: Test issue creation
- `debug_project.py`: Test project access
- `debug_plugins.py`: Test plugin access
- `debug_fix.py`: Fix common issues

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check that tokens in `config.json` are valid
2. **Connection Errors**: Verify `base_url` is correct and accessible
3. **Discovery Failures**: Check API permissions for the token user
4. **Monitoring Errors**: Ensure SSH access to target servers (if using monitoring)

### Getting Help

- Review execution logs: `execution_<RUN_ID>.log`
- Check Locust HTML report for detailed request/response information
- Verify token permissions in Jira

## Example Workflow

```bash
# 1. Configure environment
# Edit config.json and add your tokens

# 2. Run resiliency test
./run_test.sh dev resiliency

# 3. Wait for completion (2 hours for resiliency profile)

# 4. Review results
# Extract results_<RUN_ID>.tar.gz
# Open report_<RUN_ID>.html in browser
# Review metrics_<RUN_ID>.csv for infrastructure data
```

## Files Overview

- `config.json`: Main configuration file
- `locustfile.py`: Locust test definitions
- `discover.py`: Resource discovery script
- `monitor.py`: Infrastructure monitoring script
- `run_test.sh`: Main execution script
- `debug_*.py`: Debug and troubleshooting scripts

---

**Note**: This is production-ready code. Ensure all "TOKEN" placeholders are replaced with actual values before execution.

