#!/bin/bash

# Usage: 
#   ./analyze_buckets.sh < broadcom_jira_groups.txt
#   OR
#   cat broadcom_jira_groups.txt | grep -i "ATL_Apps" | ./analyze_buckets.sh

echo "---------------------------------------------------------"
echo "Analyzing Group Membership Counts..."
echo "---------------------------------------------------------"

awk -F'|' '
BEGIN {
    # Initialize buckets to 0 to avoid empty printouts
    b0=0; b1=0; b2=0; b3_5=0; b6_10=0; b11_20=0; b_gt20=0; total=0
}
{
    # Field $4 is the count. strip whitespace.
    gsub(/ /, "", $4)
    raw_count = $4

    # Logic: Convert to integer. 
    # If it contains "+", treat it as a large number (e.g. 1500+ -> 999999)
    if (index(raw_count, "+") > 0) {
        count = 999999 
    } else {
        count = raw_count + 0 
    }

    # Increment Total
    total++

    # Bucket Logic
    if (count == 0) {
        b0++
    } else if (count == 1) {
        b1++
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
    }
}
END {
    # Helper function to print row with percentage
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
}

function print_row(label, val, tot, format_str) {
    if (tot > 0) pct = (val / tot) * 100
    else pct = 0
    printf format_str, label, val, sprintf("%.2f%%", pct)
}
'
