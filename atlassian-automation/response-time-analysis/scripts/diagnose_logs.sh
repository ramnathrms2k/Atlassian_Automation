#!/usr/bin/env bash
# Diagnose access logs via SSH (passwordless ssh as $SSH_USER to $NODE).
# Usage: ./scripts/diagnose_logs.sh [product] [date] [to_date] [grep_pattern]
# Example: ./scripts/diagnose_logs.sh jira 2026-02-10 2026-02-10 'selectPageId=98308'
# Optional env: SSH_USER=svcjira NODE=... LOG_PATH=... LOG_FILE=...
# For Confluence: NODE=conf-lvnv-it-101.lvn.broadcom.net LOG_PATH=/export/confluence/logs LOG_FILE_TEMPLATE=conf_access_log.%Y-%m-%d.log

set -e
SSH_USER="${SSH_USER:-svcjira}"
NODE="${NODE:-jira-lvnv-it-101.lvn.broadcom.net}"
LOG_PATH="${LOG_PATH:-/export/jira/logs}"
PATTERN="${4:-Dashboard.jspa}"

if [ -n "$2" ]; then
  FROM="$2"
else
  FROM=$(date +%Y-%m-%d)
fi
if [ -n "$3" ]; then
  TO="$3"
else
  TO="$FROM"
fi
# Log file name: Confluence uses conf_access_log.YYYY-MM-DD.log, Jira uses access_log.YYYY-MM-DD
if [ -n "$LOG_FILE_TEMPLATE" ]; then
  LOG_FILE="$(echo "$LOG_FILE_TEMPLATE" | sed "s/%Y-%m-%d/$TO/g")"
else
  LOG_FILE="access_log.$TO"
fi

echo "=== Log path: $LOG_PATH, node: $NODE, user: $SSH_USER ==="
echo "=== Date range: $FROM to $TO, grep pattern: $PATTERN ==="
echo ""

# List log files
echo "--- Log files (last 15) ---"
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$NODE" "ls -la $LOG_PATH/ | tail -15"
echo ""

# Count matches for the given day(s)
echo "--- Line count for pattern '$PATTERN' ---"
file="$LOG_PATH/$LOG_FILE"
count=$(ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$NODE" "grep -c -F '$PATTERN' $file 2>/dev/null || echo 0")
echo "$TO ($file): $count lines"

echo ""
echo "--- Sample lines (first 3) ---"
ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$NODE" "grep -F '$PATTERN' $file 2>/dev/null | head -3" || echo "(no matches or error)"
