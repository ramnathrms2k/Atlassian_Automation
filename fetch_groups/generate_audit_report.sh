#!/bin/bash

# Usage: 
#   cat broadcom_jira_groups.txt | grep -i "ATL_Apps" | ./generate_audit_report.sh

# Output Files
FILE_EMPTY="audit_action_delete.csv"
FILE_SINGLE="audit_action_assign_owner.csv"
FILE_LARGE="audit_review_permissions.csv"

# Write Headers to CSVs
echo "Group Name,Primary Attribute,Owner,Member Count" > "$FILE_EMPTY"
echo "Group Name,Primary Attribute,Owner,Member Count" > "$FILE_SINGLE"
echo "Group Name,Primary Attribute,Owner,Member Count" > "$FILE_LARGE"

echo "---------------------------------------------------------"
echo "Generating Audit Files & Analyzing Counts..."
echo "---------------------------------------------------------"

awk -F'|' -v f_empty="$FILE_EMPTY" -v f_single="$FILE_SINGLE" -v f_large="$FILE_LARGE" '
BEGIN {
    # Initialize buckets
    b0=0; b1=0; b2=0; b3_5=0; b6_10=0; b11_20=0; b_gt20=0; total=0
}
{
    # Clean up variables (Trim whitespace)
    gsub(/^ +| +$/, "", $1); name=$1
    gsub(/^ +| +$/, "", $2); primary=$2
    gsub(/^ +| +$/, "", $3); owner=$3
    gsub(/ /, "", $4); raw_count=$4

    # Handle "1500+" logic
    if (index(raw_count, "+") > 0) {
        count = 999999 
    } else {
        count = raw_count + 0 
    }

    total++

    # CSV Output Line Format
    csv_line = name "," primary "," owner "," raw_count

    # --- BUCKET LOGIC ---
    if (count == 0) {
        b0++
        print csv_line >> f_empty
    } else if (count == 1) {
        b1++
        print csv_line >> f_single
    } else if (count == 2) {
        b2++
    } else if (count >= 3 && count <= 5) {
        b3_5++
    } else if (count >= 6 && count <= 10) {
        b6_10++
    } else if (count >= 11 && count <= 20) {
        b11_20++
    } else {
        b_gt20++
        print csv_line >> f_large
    }
}
END {
    # Print Summary Table
    fmt = "%-20s | %-10s | %s\n"
    
    printf fmt, "Bucket Category", "Count", "Percentage"
    printf "---------------------------------------------------------\n"
    
    print_row("0 Members", b0, total, fmt)
    print_row("1 Member", b1, total, fmt)
    print_row("2 Members", b2, total, fmt)
    print_row("3 - 5 Members", b3_5, total, fmt)
    print_row("6 - 10 Members", b6_10, total, fmt)
    print_row("11 - 20 Members", b11_20, total, fmt)
    print_row("> 20 Members", b_gt20, total, fmt)
    
    printf "---------------------------------------------------------\n"
    printf fmt, "Total Groups", total, "100%"
    
    print "\n[Audit Files Generated]"
    print "1. " f_empty " (Safe to delete?)"
    print "2. " f_single " (Needs backup owner)"
    print "3. " f_large " (Review for admin rights)"
}

function print_row(label, val, tot, format_str) {
    if (tot > 0) pct = (val / tot) * 100
    else pct = 0
    printf format_str, label, val, sprintf("%.2f%%", pct)
}
'
