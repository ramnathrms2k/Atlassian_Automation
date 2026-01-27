# Troubleshooting Guide

## Issue 1: Flask SECRET_KEY Error ✅ FIXED

**Error**: `RuntimeError: The session is unavailable because no secret key was set`

**Fix Applied**: Added `app.secret_key` to `app.py`

**Status**: ✅ Fixed - Restart the app and try again

---

## Issue 2: SSH Connection Issues

### If passwordless SSH was set up AFTER opening the terminal:

**Solution**: Yes, you should open a new terminal window/tab. SSH key authentication is typically loaded when the terminal session starts, so if you:
1. Opened terminal
2. Then ran `ssh-keygen` and `ssh-copy-id`
3. The current terminal session might not have the new SSH keys loaded

**To Fix**:
1. Open a **new terminal window/tab**
2. Navigate to the framework directory
3. Test SSH manually first:
   ```bash
   ssh svcjira@jira-lvnv-it-101.lvn.broadcom.net "echo 'SSH test successful'"
   ```
4. If that works, restart the Flask app in the new terminal

### Verify SSH Setup:
```bash
# Test each server
ssh svcjira@jira-lvnv-it-101.lvn.broadcom.net "hostname"
ssh svcjira@jira-lvnv-it-102.lvn.broadcom.net "hostname"
ssh svcjira@jira-lvnv-it-103.lvn.broadcom.net "hostname"
ssh svcjira@db-lvnv-it-101.lvn.broadcom.net "hostname"
```

All should work without password prompts.

---

## Issue 3: Configuration Not Loading

### Verify Credentials are Set:

1. **Check `instances_config.py`**:
   ```python
   # Should have actual values (not "TOKEN"):
   "jira_pat": "TOKEN"  # Use environment variable JIRA_OPS_VMW_JIRA_PROD_JIRA_PAT
   "db_password": "TOKEN"  # Use environment variable JIRA_OPS_VMW_JIRA_PROD_DB_PASSWORD
   ```

2. **Check framework config files**:
   - `frameworks/health_dashboard/config.py` - Should read from injected config
   - `frameworks/response_tracker/config.py` - Has hardcoded values (OK for now)
   - `frameworks/preflight_validator/config.py` - Has hardcoded values (OK for now)

### Test Config Loading:
```python
# In Python shell (from framework directory):
from config_manager import get_instance_config
config = get_instance_config('vmw-jira-prod')
print(config['credentials']['jira_pat'])  # Should show actual token
print(config['credentials']['db_password'])  # Should show actual password
```

---

## Issue 4: Framework Routes Not Found

**Current Status**: Frameworks need to be properly integrated as routes.

**Quick Test**: Try accessing frameworks directly:
- The frameworks are copied but may need route registration
- For now, you can test by running frameworks standalone to verify config works

**Next Steps**: We may need to register framework routes in the main app, or use a different integration approach.

---

## Quick Verification Checklist

- [ ] Flask app starts without errors
- [ ] Can access `http://localhost:8000` (main page loads)
- [ ] Framework selection page shows 4 frameworks
- [ ] Instance selection shows "VMW-Jira-Prod"
- [ ] SSH works from NEW terminal: `ssh svcjira@jira-lvnv-it-101.lvn.broadcom.net`
- [ ] Credentials in `instances_config.py` are actual values (not "TOKEN")
- [ ] Framework config files exist and have correct values

---

## Testing SSH in New Terminal

1. **Open new terminal**
2. **Test SSH**:
   ```bash
   ssh svcjira@jira-lvnv-it-101.lvn.broadcom.net "echo 'SSH works'"
   ```
3. **If SSH works**, restart Flask app in this new terminal:
   ```bash
   cd /Users/ramanathanm/Downloads/atlassian-automation-pregit-01092026/gto-ATL-Jira-ops-center
   python app.py
   ```

---

## Common Issues Summary

| Issue | Solution | Status |
|-------|----------|--------|
| SECRET_KEY error | Added to app.py | ✅ Fixed |
| SSH not working | Use new terminal | ⚠️ Try new terminal |
| Config not loading | Verify instances_config.py | ✅ Should work |
| Framework routes | Needs integration | 🔄 In progress |
