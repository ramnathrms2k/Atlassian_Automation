#!/bin/bash

# --- Configuration ---
DB_USER="atlassian_readonly"
DB_PASS="TOKEN"
DB_HOST="db-lvnv-it-115.lvn.broadcom.net"
DB_NAME="jiradb"
INPUT_FILE="customfields.txt"
OUTPUT_FILE="customfield_usage_report.csv"
# ---------------------

# Create the CSV header
echo "custom_field_id,custom_field_name,project_key,issue_count_with_data,last_touched_date" > $OUTPUT_FILE

# Read the input file line by line (it's tab-separated)
while IFS=$'\t' read -r CF_ID CF_NAME
do
    echo "Processing Custom Field ID: $CF_ID ($CF_NAME)..."

    # This is your Query 1, but optimized to run for *only one field*
    QUERY="
    SELECT
        p.pkey,
        COUNT(DISTINCT i.id),
        MAX(i.updated)
    FROM
        customfieldvalue cfv
    JOIN
        jiraissue i ON cfv.issue = i.id
    JOIN
        project p ON i.project = p.id
    WHERE
        cfv.customfield = ${CF_ID}
    GROUP BY
        p.pkey;
    "

    # Run the small query and loop through its results (if any)
    # -s (silent) and -N (no headers) are for clean output
    mysql -u$DB_USER -p$DB_PASS -h$DB_HOST $DB_NAME -s -N -e "$QUERY" | while IFS=$'\t' read -r PROJ_KEY COUNT DATE
    do
        # Write the combined data to our final CSV file
        echo "${CF_ID},\"${CF_NAME}\",\"${PROJ_KEY}\",${COUNT},\"${DATE}\"" >> $OUTPUT_FILE
    done

done < "$INPUT_FILE"

echo "Done. Report saved to $OUTPUT_FILE"
