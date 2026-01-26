#!/bin/bash

# --- Configuration ---
# vvv SET YOUR PRODUCTION READ-ONLY DB DETAILS HERE vvv
DB_USER="atlassian_readonly"
DB_PASS="R3@d0n7y@123"
DB_HOST="db-lvnv-it-102.lvn.broadcom.net"       
DB_NAME="jiradb"
# ^^^ SET YOUR PRODUCTION READ-ONLY DB DETAILS HERE ^^^

INPUT_FILE="final_audit_list.txt" # <-- This is the combined list of 216 fields
OUTPUT_FILE="customfield_usage_report_PROD.csv"
# ---------------------

# Create the CSV header
echo "custom_field_id,custom_field_name,project_key,issue_count_with_data,last_touched_date" > $OUTPUT_FILE

# Read the input file (which is just a list of IDs)
while read -r CF_ID
do
    # Get the CF name from prod
    CF_NAME=$(mysql -u$DB_USER -p$DB_PASS -h$DB_HOST $DB_NAME -s -N -e "SELECT cfname FROM customfield WHERE id = ${CF_ID};")
    
    echo "Processing (PROD-VERIFY) Field ID: $CF_ID ($CF_NAME)..."
    
    # This is the detailed usage query
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
    mysql -u$DB_USER -p$DB_PASS -h$DB_HOST $DB_NAME -s -N -e "$QUERY" | while IFS=$'\t' read -r PROJ_KEY COUNT DATE
    do
        # Write the combined data to our final CSV file
        # Escaping any quotes in the custom field name
        CF_NAME_ESCAPED=$(echo "$CF_NAME" | sed 's/"/""/g')
        echo "${CF_ID},\"${CF_NAME_ESCAPED}\",\"${PROJ_KEY}\",${COUNT},\"${DATE}\"" >> $OUTPUT_FILE
    done

done < "$INPUT_FILE"

echo "Done. Production-verified raw report saved to $OUTPUT_FILE"
