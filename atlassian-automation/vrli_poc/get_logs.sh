#!/bin/bash

# Usage: ./get_logs.sh <QUERY_ANCHOR> <OUTPUT_NAME> [OPTIONAL_ARGS]

QUERY=$1
NAME=$2
EXTRA_ARGS="${@:3}" # Passes any extra flags like --host or --file directly to Python

if [ -z "$QUERY" ] || [ -z "$NAME" ]; then
  echo "Usage:   ./get_logs.sh <SEARCH_TERM> <REPORT_NAME> [FILTERS]"
  echo "Example: ./get_logs.sh 'dn023350' 'user_activity' --file conf_access"
  echo "Example: ./get_logs.sh 'OutOfMemory' 'oom_errors' --host conf-lvnv-it-1 --days 30"
  exit 1
fi

echo "---------------------------------------------------------"
echo "[1/2] Fetching Logs for '$QUERY'..."
echo "---------------------------------------------------------"

# Run the fetcher
python3 vrli_fetch.py --query "$QUERY" $EXTRA_ARGS > "${NAME}.json"

# Check if JSON is valid/not empty
if [ ! -s "${NAME}.json" ]; then
  echo "[-] No data found. Check your search terms."
  rm "${NAME}.json"
  exit 1
fi

echo "---------------------------------------------------------"
echo "[2/2] Converting to CSV..."
echo "---------------------------------------------------------"

# Run the converter
python3 json_to_csv_v2.py "${NAME}.json" "${NAME}.csv"

echo "[+] SUCCESS: Report saved to ${NAME}.csv"
