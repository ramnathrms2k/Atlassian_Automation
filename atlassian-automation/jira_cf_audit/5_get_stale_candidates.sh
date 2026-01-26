#!/bin/bash

# This script reads the summary report and creates a list of "stale"
# field IDs based on a hardcoded cutoff date.

INPUT_FILE="customfield_summary_report.csv"
OUTPUT_FILE="stale_candidates.txt"
CUTOFF_DATE="2023-01-01"

echo "Finding stale fields from $INPUT_FILE..."
echo "Using cutoff date: $CUTOFF_DATE"

# awk reads the CSV. -F',' sets the delimiter to a comma.
# NR > 1 skips the header row.
# $4 is the date field. We remove quotes and compare it.
# If it's less than the cutoff, we print $1 (the ID).
awk -F',' 'NR > 1 {
    # Remove quotes from the date field for string comparison
    gsub(/"/, "", $4)
    
    if ($4 < "'$CUTOFF_DATE'") {
        print $1
    }
}' "$INPUT_FILE" > "$OUTPUT_FILE"

COUNT=$(wc -l < "$OUTPUT_FILE")
echo "Done. Found $COUNT stale field IDs."
echo "Saved list to $OUTPUT_FILE"
