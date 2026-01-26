# Fixed Git Commands - Correct Sequence

## Issue
You cloned the repo into `Devops` directory, but you're still in `atlassian-automation` directory. You need to navigate into `Devops` first.

---

## Corrected Commands

Run these commands in sequence:

```bash
# 1. Navigate to Downloads (where Devops was cloned)
cd /Users/ramanathanm/Downloads

# 2. Go into the Devops repository
cd Devops

# 3. Checkout/create the branch
git checkout Atlassian_automation || git checkout -b Atlassian_automation

# 4. Copy the automation folder (from parent directory)
cp -r ../atlassian-automation .

# 5. Check what will be added
git status

# 6. Stage and commit
git add atlassian-automation/
git commit -m "Add Atlassian automation frameworks and scripts

- Added comprehensive automation frameworks for Jira/Confluence
- Sanitized all tokens and passwords
- Added README documentation for each framework"

# 7. Push to remote
git push origin Atlassian_automation
```

---

## Quick Fix (Copy-Paste Ready)

```bash
cd /Users/ramanathanm/Downloads/Devops
git checkout Atlassian_automation || git checkout -b Atlassian_automation
cp -r ../atlassian-automation .
git add atlassian-automation/
git commit -m "Add Atlassian automation frameworks and scripts

- Added comprehensive automation frameworks for Jira/Confluence
- Sanitized all tokens and passwords
- Added README documentation for each framework"
git push origin Atlassian_automation
```

---

## What Was Wrong

1. **Wrong Directory**: You were in `atlassian-automation` but git repo is in `Devops`
2. **Copy Path**: Need to copy from `../atlassian-automation` (parent directory) not from absolute path when already in Devops

---

**Run the commands above from the `Devops` directory!**

