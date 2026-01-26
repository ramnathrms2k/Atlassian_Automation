#!/bin/bash

# Usage: ./run_stats.sh --app <jira|confluence> --type <human|service> [OPTIONS]

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Defaults
LIMIT=5000; DAYS=7; THRESHOLD=1000; QUERY=""; AUTH_USER=""; AUTH_PASS=""
# Arrays for multiple includes
INCLUDES=()

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --app) APP="$2"; shift ;; --type) TYPE="$2"; shift ;; 
        --limit) LIMIT="$2"; shift ;; --days) DAYS="$2"; shift ;; 
        --threshold) THRESHOLD="$2"; shift ;;
        # NEW: Allow explicit query anchor
        --query) QUERY="$2"; shift ;;
        # NEW: Allow multiple includes
        --include) INCLUDES+=("$2"); shift ;;
        --user) AUTH_USER="$2"; shift ;; --password) AUTH_PASS="$2"; shift ;; 
        *) echo "Unknown: $1"; exit 1 ;;
    esac; shift
done

if [ -z "$APP" ] || [ -z "$TYPE" ]; then 
    echo "Usage: ./run_stats.sh --app <app> --type <type> [--query 'ANCHOR'] [--include 'FILTER']"
    exit 1
fi

if [ "$APP" == "jira" ]; then FILE="access_log"; HOST="jira-lvnv-it"; 
elif [ "$APP" == "confluence" ]; then FILE="conf_access"; HOST="conf-lvnv-it"; fi

# Set Anchor: Use provided query, or default to HTTP (Broad search)
ANCHOR="${QUERY:-HTTP}"

CRED_ARGS=""; if [ -n "$AUTH_USER" ]; then CRED_ARGS="$CRED_ARGS --auth-user $AUTH_USER"; fi
if [ -n "$AUTH_PASS" ]; then CRED_ARGS="$CRED_ARGS --password $AUTH_PASS"; fi

# Build include arguments for Python
INCLUDE_ARGS=""
for inc in "${INCLUDES[@]}"; do
    INCLUDE_ARGS="$INCLUDE_ARGS --include $inc"
done

echo "-----------------------------------------------------------"
echo "[*] Fetching $LIMIT events for $APP..."
echo "    Anchor: '$ANCHOR' | Filters: ${INCLUDES[*]}"
echo "-----------------------------------------------------------"

python3 "$SCRIPT_DIR/vrli_fetch.py" --query "$ANCHOR" --file "$FILE" --host "$HOST" --limit "$LIMIT" --days "$DAYS" $CRED_ARGS $INCLUDE_ARGS > "stats_raw.json"

if [ ! -s "stats_raw.json" ]; then echo "[-] No data fetched."; exit 1; fi

echo "[*] Analyzing..."
python3 "$SCRIPT_DIR/access_log_stats.py" --file "stats_raw.json" --app "$APP" --type "$TYPE" --threshold "$THRESHOLD" $INCLUDE_ARGS

# rm "stats_raw.json"
