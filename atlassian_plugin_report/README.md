# Atlassian Plugin Report

## Overview

A comprehensive framework for auditing and reporting on Atlassian (Jira/Confluence) plugins and marketplace apps. This framework fetches plugin information, checks pricing, and generates reports for license compliance and cost analysis.

## What It Does

- **Plugin Discovery**: Fetches all installed plugins from Jira/Confluence instances
- **Marketplace Integration**: Retrieves plugin pricing and metadata from Atlassian Marketplace
- **License Reporting**: Generates reports on plugin licenses and compliance
- **Cost Analysis**: Analyzes plugin costs and subscription information
- **Multi-Server Support**: Supports multiple Jira/Confluence instances
- **Multiple Scraping Methods**: Supports API, Selenium, and Playwright for marketplace data

## Prerequisites

- Python 3.7+
- Access to Jira/Confluence instances with API tokens
- Network access to Atlassian Marketplace (for pricing data)
- Optional: Selenium/Playwright for advanced scraping (if API method doesn't work)

## Configuration

### Main Configuration File: `servers_config.json`

Edit `servers_config.json` to configure Jira/Confluence instances:

```json
{
  "servers": [
    {
      "name": "Jira-Prod",
      "url": "https://jira.example.com",
      "token": "TOKEN"
    },
    {
      "name": "Confluence-Prod",
      "url": "https://confluence.example.com",
      "token": "TOKEN"
    }
  ]
}
```

**Configuration Parameters:**
- `name`: Descriptive name for the instance
- `url`: Base URL of Jira/Confluence instance
- `token`: Jira/Confluence API token (Personal Access Token)
  - **Replace "TOKEN" with actual tokens** from Account Settings → Security → API Tokens

### Alternative Configuration: Inline (jiraconf_plugins_list_v4.py)

Some scripts have inline configuration:

```python
SERVERS = [
    {
        "name": "Jira-Prod",
        "url": "https://jira.example.com",
        "token": "TOKEN"  # Replace with actual token
    }
]
```

### Server Names and Locations

- **Jira/Confluence URLs**: Configured in `servers_config.json` or inline in scripts
- **Marketplace URL**: Hardcoded to Atlassian Marketplace (no configuration needed)

### Thresholds

- **API Rate Limits**: Be aware of API rate limits when querying multiple instances
- **Scraping Delays**: Built-in delays to avoid overwhelming marketplace servers

## How to Use

### 1. Setup

```bash
# Install dependencies
pip install requests

# For Selenium scraping (optional)
pip install selenium

# For Playwright scraping (optional)
pip install playwright
playwright install
```

### 2. Configure Tokens

Edit `servers_config.json` and replace all "TOKEN" placeholders with actual API tokens.

### 3. Run Reports

```bash
# Main plugin report (uses servers_config.json)
python3 atlassian_plugin_report_v6.py

# Alternative script (inline configuration)
python3 jiraconf_plugins_list_v4.py

# Price scraper (API method)
python3 atlassian_price_scrapper_api.py

# Price scraper (Selenium method - if API fails)
python3 atlassian_price_scrapper_selenium.py

# Price scraper (Playwright method - if API fails)
python3 atlassian_price_scrapper_playright.py
```

## Credentials/Tokens

### Getting API Tokens

1. Log into Jira/Confluence
2. Go to: **Account Settings → Security → API Tokens**
3. Click **Create API Token**
4. Copy the token and add it to `servers_config.json`

**Important**: Replace all "TOKEN" placeholders in configuration files with actual tokens.

### Security Notes

- **Never commit tokens to version control**
- Use separate tokens for different environments
- Rotate tokens periodically
- Use read-only tokens when possible

## Scraping Methods

The framework supports multiple methods for fetching marketplace data:

1. **API Method** (`atlassian_price_scrapper_api.py`): Fastest, preferred method
2. **Selenium Method** (`atlassian_price_scrapper_selenium.py`): Fallback if API fails
3. **Playwright Method** (`atlassian_price_scrapper_playright.py`): Alternative fallback

## Troubleshooting

### Common Issues

1. **401 Unauthorized**: Check that tokens in `servers_config.json` are valid
2. **Connection Errors**: Verify URLs are correct and accessible
3. **Marketplace Scraping Fails**: Try alternative scraping method (Selenium/Playwright)
4. **Rate Limiting**: Add delays between requests if hitting rate limits

### Getting Help

- Review error messages in console output
- Verify token permissions in Jira/Confluence
- Check network connectivity to instances and marketplace

## Example Workflow

```bash
# 1. Configure servers
# Edit servers_config.json and add your instances with tokens

# 2. Run plugin report
python3 atlassian_plugin_report_v6.py

# 3. Review output
# Check console output and generated reports
```

## Files Overview

- `atlassian_plugin_report_v6.py`: Main plugin reporting script
- `jiraconf_plugins_list_v4.py`: Alternative plugin list script
- `servers_config.json`: Server configuration file
- `atlassian_price_scrapper_api.py`: Marketplace price scraper (API)
- `atlassian_price_scrapper_selenium.py`: Marketplace price scraper (Selenium)
- `atlassian_price_scrapper_playright.py`: Marketplace price scraper (Playwright)
- `atlassian_price_scrapper.py`: Base price scraper

---

**Note**: This is production-ready code. Replace all "TOKEN" placeholders in `servers_config.json` with actual API tokens before execution.

