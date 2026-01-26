#!/bin/bash

# --- Configuration ---
DB_USER="atlassian_readonly"
DB_PASS="R3@d0n7y@123"
DB_HOST="db-lvnv-it-115.lvn.broadcom.net"
DB_NAME="jiradb"
INPUT_FILE="low_hanging_fruit.csv"
# ---------------------

echo "Verifying empty fields from $INPUT_FILE..."
ERROR_COUNT=0
PROCESSED_COUNT=0

# --- FIX IS HERE ---
# Get the total count first (subtract 1 for header)
TOTAL_FIELDS=$(($(wc -l < "$INPUT_FILE") - 1))
# -----------------

# Read the input CSV, skip header (NR > 1), get first column ($1)
awk -F',' 'NR > 1 {print $1}' "$INPUT_FILE" | while read -r CF_ID
do
    QUERY="SELECT COUNT(*) FROM customfieldvalue WHERE customfield = ${CF_ID};"
    COUNT=$(mysql -u$DB_USER -p$DB_PASS -h$DB_HOST $DB_NAME -s -N -e "$QUERY")

    if [ "$COUNT" -gt 0 ]; then
        echo "!! ERROR !! Field ID $CF_ID was supposed to be empty, but has $COUNT issues!"
        let ERROR_COUNT++
    fi
    
    let PROCESSED_COUNT++

    if [ $(($PROCESSED_COUNT % 100)) -eq 0 ]; then
        echo "  ...verified $PROCESSED_COUNT fields."
    fi
done

echo "--- Verification Complete ---"
if [ "$ERROR_COUNT" -eq 0 ]; then
    # --- AND HERE ---
    echo "✅ SUCCESS: All $TOTAL_FIELDS fields are confirmed empty."
else
    # --- AND HERE ---
    echo "❌ FAILED: Found $ERROR_COUNT fields that were not empty (out of $TOTAL_FIELDS total)."
fi
