#!/bin/bash

# Usage: ./run_test.sh <env> <profile>
ENV=$1
PROFILE=$2

if [ -z "$ENV" ] || [ -z "$PROFILE" ]; then
  echo "Usage: ./run_test.sh <env> <profile>"
  exit 1
fi

TIMESTAMP=$(date +"%Y%m%d_%H%M")
RUN_ID="${ENV}_${PROFILE}_${TIMESTAMP}"

echo "---------------------------------------------------"
echo "🚀 INITIALIZING TOUCHLESS RUN: $RUN_ID"
echo "---------------------------------------------------"

# 1. Start Telemetry (Background)
echo "📡 Starting Infrastructure Monitor..."
# Ensure the python script knows where the DB is
python3 monitor.py --run_id "$RUN_ID" --action start > "monitor_${RUN_ID}.log" 2>&1 &
MONITOR_PID=$!
echo "   Monitor PID: $MONITOR_PID"

# 2. Run Discovery
echo "🔍 Starting Discovery..."
python3 discover.py --env "$ENV" --run_id "$RUN_ID" --profile "$PROFILE"
if [ $? -ne 0 ]; then
    echo "❌ Discovery failed. Killing monitor."
    kill $MONITOR_PID
    exit 1
fi

# 3. Run Locust (Foreground for 'nohup' wrapper)
LOG_FILE="execution_${RUN_ID}.log"
REPORT_FILE="report_${RUN_ID}.html"

echo "🔥 Starting Load Test..."
echo "   Log File:    $LOG_FILE"
echo "   HTML Report: $REPORT_FILE"

export RUN_ID
export TARGET_ENV=$ENV
export TEST_PROFILE=$PROFILE

# Run locust in background but wait for it
nohup python3 -m locust -f locustfile.py --headless --html "$REPORT_FILE" > "$LOG_FILE" 2>&1 &
LOCUST_PID=$!

echo "⏳ Test running with PID $LOCUST_PID. Waiting for completion..."
wait $LOCUST_PID

echo "✅ Load Test Finished."

# 4. Stop Telemetry
echo "🛑 Stopping Monitor..."
kill $MONITOR_PID
sleep 5 # Give it a second to flush files

# 5. Generate Graphs
echo "📊 Generating Graphs..."
python3 monitor.py --run_id "$RUN_ID" --action plot

# 6. Compress Results (The New Step)
echo "📦 Compressing Results..."
ARCHIVE_NAME="results_${RUN_ID}.tar.gz"
# This grabs every file containing the RUN_ID (logs, csv, json, html, png)
tar -czf "$ARCHIVE_NAME" *"${RUN_ID}"* --exclude="$ARCHIVE_NAME"

echo "==================================================="
echo "🎉 RUN COMPLETE"
echo "   Download this single file:"
echo "   👉 $ARCHIVE_NAME"
echo "==================================================="
