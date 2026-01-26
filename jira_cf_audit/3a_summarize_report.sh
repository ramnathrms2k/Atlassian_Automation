#!/bin/bash
# This script reads the raw report and creates a summary.

INPUT_FILE="customfield_usage_report.csv"
OUTPUT_FILE="customfield_summary_report.csv"

echo "Summarizing data from $INPUT_FILE..."

awk '
BEGIN {
    FS = ","  # Set input field separator to comma
    OFS = "," # Set output field separator to comma

    # Print the header for our new summary file
    print "custom_field_id,custom_field_name,total_issue_count,latest_touched_date,project_list"
}

# Skip the header line of the input file
NR > 1 {
    # $1=id, $2=name, $3=proj, $4=count, $5=date

    # Remove quotes from the text fields for processing
    gsub(/"/, "", $2) # cf_name
    gsub(/"/, "", $3) # project_key
    gsub(/"/, "", $5) # last_touched_date

    cf_id = $1

    # Store the name (it will be the same for each ID)
    names[cf_id] = $2

    # Add to the total count for this ID
    counts[cf_id] += $4

    # Check if this date is the latest one we have seen for this ID
    if (dates[cf_id] == "" || $5 > dates[cf_id]) {
        dates[cf_id] = $5
    }

    # Add the project to a list for this ID
    # (This prevents adding the same project key twice)
    if (projects[cf_id] == "") {
        projects[cf_id] = $3
    } else if (projects[cf_id] !~ $3) {
        projects[cf_id] = projects[cf_id] ";" $3
    }
}

END {
    # Once all lines are read, loop through all the IDs we found
    # and print the summarized data.
    n = asorti(counts, sorted_ids)
    for (i = 1; i <= n; i++) {
        id = sorted_ids[i]

        # Print the final CSV line, re-adding quotes for text fields
        print id, "\"" names[id] "\"", counts[id], "\"" dates[id] "\"", "\"" projects[id] "\""
    }
}
' "$INPUT_FILE" > "$OUTPUT_FILE"

echo "Done. 'Analysis List' saved to $OUTPUT_FILE"
