#!/bin/bash

# This script summarizes the FINAL production-verified "stale/error" report

INPUT_FILE="customfield_usage_report_PROD.csv"
OUTPUT_FILE="final_summary_report_STALE.csv"

echo "Summarizing data from $INPUT_FILE..."

awk '
BEGIN {
    FS = ","
    OFS = ","
    print "custom_field_id,custom_field_name,total_issue_count,latest_touched_date,project_list"
}
NR > 1 {
    gsub(/"/, "", $2) # cf_name
    gsub(/"/, "", $3) # project_key
    gsub(/"/, "", $5) # last_touched_date
    cf_id = $1
    names[cf_id] = $2
    counts[cf_id] += $4
    if (dates[cf_id] == "" || $5 > dates[cf_id]) {
        dates[cf_id] = $5
    }
    if (projects[cf_id] == "") {
        projects[cf_id] = $3
    } else if (projects[cf_id] !~ $3) {
        projects[cf_id] = projects[cf_id] ";" $3
    }
}
END {
    n = asorti(counts, sorted_ids)
    for (i = 1; i <= n; i++) {
        id = sorted_ids[i]
        print id, "\"" names[id] "\"", counts[id], "\"" dates[id] "\"", "\"" projects[id] "\""
    }
}
' "$INPUT_FILE" > "$OUTPUT_FILE"

echo "Done. 'Stale/Error' summary saved to $OUTPUT_FILE"
