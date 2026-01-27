# Testing Guide - GTO ATL Jira Operations Center

## Confidence Level Assessment

**Confidence Level: HIGH (85-90%)**

### Why High Confidence:

1. **Framework Maturity**: All 4 frameworks are already tested and working in production
2. **Simple Integration**: Phase 1 uses minimal code changes - just config injection
3. **Proven Patterns**: Configuration injection is a well-established pattern
4. **Low Risk**: Frameworks remain independent and can run standalone

### Potential Issues:

1. **Config Injection Timing**: Frameworks need to read injected config at the right time
2. **Path/Import Issues**: Python import paths may need adjustment
3. **Template Paths**: Flask template paths may need configuration

## Pre-Testing Checklist

- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `instances_config.py` has valid VMW-Jira-Prod configuration
- [ ] Credentials set (either in config or environment variables)
- [ ] SSH access verified to all Jira nodes
- [ ] Original frameworks tested and working

## Testing Steps

### 1. Basic Application Test

```bash
cd /Users/ramanathanm/Downloads/atlassian-automation-pregit-01092026/gto-ATL-Jira-ops-center
python app.py
```

**Expected Result:**
- Application starts on port 8000
- No errors in console
- Can access `http://localhost:8000`

**What to Look For:**
- ✅ Main page loads with 4 framework cards
- ✅ No Python import errors
- ✅ No configuration errors

### 2. Framework Selection Test

1. Open browser: `http://localhost:8000`
2. Click on "Health Dashboard" card

**Expected Result:**
- Redirects to instance selection page
- Shows dropdown with "VMW-Jira-Prod"
- "Launch Framework" button visible

**What to Look For:**
- ✅ Instance selection page loads
- ✅ Dropdown shows VMW-Jira-Prod
- ✅ No JavaScript errors in browser console

### 3. Instance Selection and Launch Test

1. Select "VMW-Jira-Prod" from dropdown
2. Click "Launch Framework"

**Expected Result:**
- Framework loads with VMW-Jira-Prod configuration
- Health dashboard displays data

**What to Look For:**
- ✅ Framework page loads
- ✅ Server names show "VMW-Jira-Prod" servers
- ✅ Data appears (or loading indicators)
- ✅ No "TOKEN" placeholders in displayed data (if credentials set)

### 4. Health Dashboard Test

**Test Scenarios:**

1. **Index Health Check:**
   - Verify all 3 Jira app nodes appear
   - Check that index health data loads
   - Verify timestamps are recent

2. **System Metrics:**
   - Verify CPU, memory, disk metrics display
   - Check color coding (green/yellow/red)
   - Verify DB server metrics appear

3. **Database Connections:**
   - Verify connection counts display
   - Check utilization percentages
   - Verify threshold colors

**What to Look For:**
- ✅ All 3 app nodes + 1 DB server appear
- ✅ Metrics show actual values (not "N/A")
- ✅ Color coding works correctly
- ✅ Auto-refresh works (if enabled)

### 5. Response Time Tracker Test

1. Select "Response Time Tracker" → "VMW-Jira-Prod" → Launch

**Expected Result:**
- Three server boxes appear
- Slow request statistics display
- User IDs and counts visible

**What to Look For:**
- ✅ All 3 Jira servers appear
- ✅ Statistics table displays
- ✅ Scrollable boxes work
- ✅ Data refreshes correctly

### 6. Preflight Validator Test

1. Select "Preflight Validator" → "VMW-Jira-Prod" → Launch

**Expected Result:**
- Node validation interface loads
- Can select nodes to validate
- Validation reports generate

**What to Look For:**
- ✅ Node list appears
- ✅ Validation runs successfully
- ✅ Reports display correctly

### 7. Script Executor Test

1. Select "Script Executor" → "VMW-Jira-Prod" → Launch

**Expected Result:**
- Script execution interface loads
- Can execute scripts on nodes
- Output displays correctly

**What to Look For:**
- ✅ Server list appears
- ✅ Script execution works
- ✅ Output displays in real-time

## Common Issues and Solutions

### Issue: "Framework not found" error

**Solution:**
- Check that framework directory exists in `frameworks/`
- Verify framework module name matches in `app.py` FRAMEWORKS dict
- Check Python import paths

### Issue: "Instance not found" error

**Solution:**
- Verify `instances_config.py` has the instance ID
- Check instance ID matches exactly (case-sensitive)
- Verify `config_manager.py` can read the config

### Issue: Configuration not loading

**Solution:**
- Check that `config_manager.py` injects config correctly
- Verify framework's `config.py` reads injected config
- Check for Python import errors
- Verify credentials are set (env vars or config file)

### Issue: SSH connection failures

**Solution:**
- Test SSH manually: `ssh svcjira@<hostname>`
- Verify passwordless SSH configured
- Check SSH user has correct permissions
- Verify hostnames are correct in config

### Issue: Framework shows "TOKEN" instead of data

**Solution:**
- Set environment variables:
  ```bash
  export JIRA_OPS_VMW_JIRA_PROD_JIRA_PAT="actual_token"
  export JIRA_OPS_VMW_JIRA_PROD_DB_PASSWORD="actual_password"
  ```
- Or update `instances_config.py` with actual values (not recommended for production)

### Issue: Template not found

**Solution:**
- Verify template files exist in `templates/` directory
- Check Flask template folder configuration
- Verify template paths in framework code

## Debugging Tips

1. **Check Application Logs:**
   - Look for Python errors in console
   - Check Flask debug output
   - Review framework-specific log files

2. **Browser Developer Tools:**
   - Check Console for JavaScript errors
   - Check Network tab for failed requests
   - Verify API responses

3. **Test Individual Components:**
   - Test `config_manager.py` functions directly
   - Test framework config loading
   - Test SSH connections manually

4. **Verify Configuration:**
   ```python
   # Test in Python shell
   from config_manager import get_instance_config
   config = get_instance_config('vmw-jira-prod')
   print(config)
   ```

## Success Criteria

✅ All 4 frameworks can be launched
✅ Instance selection works for VMW-Jira-Prod
✅ Frameworks load with correct configuration
✅ Data displays correctly (or shows appropriate errors)
✅ Can switch between frameworks
✅ No critical errors in logs

## Next Steps After Testing

1. **If Issues Found:**
   - Document specific errors
   - Check framework adaptation code
   - Verify config injection timing
   - Test individual frameworks standalone

2. **If Successful:**
   - Add more instances to `instances_config.py`
   - Test with different instances
   - Consider Phase 2 enhancements

3. **Iteration:**
   - Fix any issues found
   - Re-test
   - Document learnings

## Reporting Issues

When reporting issues, include:
- Framework name
- Instance ID
- Exact error message
- Steps to reproduce
- Browser console errors (if any)
- Application log output
