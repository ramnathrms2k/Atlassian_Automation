# Correct Git Commands - Fixed for Your Situation

## Current Situation
The `Devops` repository was cloned **inside** the `atlassian-automation` directory. You need to navigate into it and copy the framework folders.

---

## Corrected Commands

Run these commands:

```bash
# 1. Navigate into the Devops repository (which is inside atlassian-automation)
cd /Users/ramanathanm/Downloads/atlassian-automation/Devops

# 2. Checkout/create the branch
git checkout Atlassian_automation || git checkout -b Atlassian_automation

# 3. Copy all framework folders (excluding Devops itself)
# Copy from parent directory, but exclude the Devops folder
rsync -av --exclude='Devops' --exclude='.git' ../ ./atlassian-automation/ 2>/dev/null || \
mkdir -p atlassian-automation && \
cp -r ../jira_load_test_framework ../vrli_framework ../jira_preflight_validator ../jira_validator ../atlassian_plugin_report ../fetch_groups ../jira_cf_audit ../jira_logparser ../vrli_poc ../sar_plotter ../atlassian_uploader ../psirt_mailhandler ../*.md atlassian-automation/ 2>/dev/null

# OR simpler: Copy everything except Devops
cd /Users/ramanathanm/Downloads/atlassian-automation
mkdir -p Devops/atlassian-automation
cp -r jira_load_test_framework vrli_framework jira_preflight_validator jira_validator atlassian_plugin_report fetch_groups jira_cf_audit jira_logparser vrli_poc sar_plotter atlassian_uploader psirt_mailhandler *.md Devops/atlassian-automation/ 2>/dev/null
cd Devops

# 4. Check what will be added
git status

# 5. Stage and commit
git add atlassian-automation/
git commit -m "Add Atlassian automation frameworks and scripts

- Added comprehensive automation frameworks for Jira/Confluence
- Sanitized all tokens and passwords
- Added README documentation for each framework"

# 6. Push to remote
git push origin Atlassian_automation
```

---

## Simpler Approach (Recommended)

```bash
# 1. Go to atlassian-automation directory
cd /Users/ramanathanm/Downloads/atlassian-automation

# 2. Create atlassian-automation folder inside Devops
mkdir -p Devops/atlassian-automation

# 3. Copy all framework folders (one by one to be safe)
cp -r jira_load_test_framework Devops/atlassian-automation/
cp -r vrli_framework Devops/atlassian-automation/
cp -r jira_preflight_validator Devops/atlassian-automation/
cp -r jira_validator Devops/atlassian-automation/
cp -r atlassian_plugin_report Devops/atlassian-automation/
cp -r fetch_groups Devops/atlassian-automation/
cp -r jira_cf_audit Devops/atlassian-automation/
cp -r jira_logparser Devops/atlassian-automation/
cp -r vrli_poc Devops/atlassian-automation/
cp -r sar_plotter Devops/atlassian-automation/
cp -r atlassian_uploader Devops/atlassian-automation/
cp -r psirt_mailhandler Devops/atlassian-automation/
cp GIT_COMMANDS.md FIXED_GIT_COMMANDS.md CORRECT_GIT_COMMANDS.md Devops/atlassian-automation/ 2>/dev/null || true

# 4. Go into Devops directory
cd Devops

# 5. Checkout/create branch
git checkout Atlassian_automation || git checkout -b Atlassian_automation

# 6. Check status
git status

# 7. Stage and commit
git add atlassian-automation/
git commit -m "Add Atlassian automation frameworks and scripts

- Added comprehensive automation frameworks for Jira/Confluence
- Sanitized all tokens and passwords
- Added README documentation for each framework"

# 8. Push
git push origin Atlassian_automation
```

---

**Run the "Simpler Approach" commands above!**

