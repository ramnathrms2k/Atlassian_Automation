#!/usr/bin/env bash
# Diagnose why DB connection count may be 0. Run from project root.
# Usage: ./scripts/diagnose_db_connections.sh [node_fqdn]
# Example: ./scripts/diagnose_db_connections.sh jira-lvnv-it-101.lvn.broadcom.net

set -e
SSH_USER="${JIRA_MONITOR_SSH_USER:-svcjira}"
DBCONFIG_PATH="/export/jirahome/dbconfig.xml"
NODES="${1:-jira-lvnv-it-101.lvn.broadcom.net jira-lvnv-it-102.lvn.broadcom.net jira-lvnv-it-103.lvn.broadcom.net}"

for NODE in $NODES; do
  echo "=============================================="
  echo "NODE: $NODE"
  echo "=============================================="
  ssh -o ConnectTimeout=10 -o BatchMode=yes "${SSH_USER}@${NODE}" bash -s << 'REMOTE'
DBCONFIG_PATH="/export/jirahome/dbconfig.xml"
echo "--- 1) dbconfig.xml: host and port (from address block) ---"
if [ -r "$DBCONFIG_PATH" ]; then
  grep -oE '\(host=[^)]+\)' "$DBCONFIG_PATH" | head -1
  grep -oE '\(port=[0-9]+\)' "$DBCONFIG_PATH" | head -1
else
  echo "File not found or not readable: $DBCONFIG_PATH"
fi

echo ""
echo "--- 2) Extract DB host for getent ---"
DBHOST=$(sed -n 's/.*(host=\([^)]*\)).*/\1/p' "$DBCONFIG_PATH" 2>/dev/null | head -1)
DBPORT=$(sed -n 's/.*(port=\([0-9]*\)).*/\1/p' "$DBCONFIG_PATH" 2>/dev/null | head -1)
echo "DBHOST=$DBHOST"
echo "DBPORT=$DBPORT"

echo ""
echo "--- 3) getent hosts \$DBHOST ---"
getent hosts "$DBHOST" 2>&1 || true

echo ""
echo "--- 4) All TCP connections (ss -tn) - lines with remote port 3306 ---"
ss -tn 2>/dev/null | awk '$5 ~ /:3306$/ {print}' || true

echo ""
echo "--- 5) ss -tpn (with process) - lines containing :3306 ---"
ss -tpn 2>/dev/null | grep ':3306' || true

echo ""
echo "--- 6) Count of connections to remote port 3306 ---"
ss -tn 2>/dev/null | awk '$5 ~ /:3306$/ {count++} END {print count+0 " connections to remote port 3306"}'

echo ""
echo "--- 7) Sample of full ss -tpn (first 25 lines) ---"
ss -tpn 2>/dev/null | head -25
REMOTE
  echo ""
done
echo "Done."
