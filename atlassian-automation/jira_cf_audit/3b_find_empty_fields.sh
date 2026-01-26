#!/bin/bash

# This script finds the fields that are empty.

INPUT_MASTER_LIST="customfields.txt"
INPUT_SUMMARY_REPORT="customfield_summary_report.csv"
OUTPUT_LOW_HANGING_FRUIT="low_hanging_fruit.csv"
TEMP_USED_IDS="used_field_ids.tmp"

echo "Extracting IDs of used fields from $INPUT_SUMMARY_REPORT..."
# Get just the first column (the ID) from the summary report, skip the header
awk -F',' 'NR > 1 {print $1}' "$INPUT_SUMMARY_REPORT" > "$TEMP_USED_IDS"

# Create the header for our new "low-hanging fruit" report
echo "custom_field_id,custom_field_name,total_issue_count,latest_touched_date,project_list" > "$OUTPUT_LOW_HANGING_FRUIT"

echo "Finding empty fields by comparing master list against used list..."

# Use grep to find all lines in the master list whose ID is NOT in the used list
grep -v -f "$TEMP_USED_IDS" "$INPUT_MASTER_LIST" | awk -F'\t' '{
    # Escape any double-quotes in the custom field name
    gsub(/"/, "\"\"", $2)

    # Print in the new CSV format with "0" and "NA"
    print $1 ",\"" $2 "\",0,\"NA\",\"NA\""
}' >> "$OUTPUT_LOW_HANGING_FRUIT"

# Clean up the temporary file
rm "$TEMP_USED_IDS"

COUNT=$(wc -l < "$OUTPUT_LOW_HANGING_FRUIT")
# Subtract 1 for the header row
let COUNT--

echo "Done. Found $COUNT empty, orphaned fields."
echo "'Easy Wins' report saved to $OUTPUT_LOW_HANGING_FRUIT"
