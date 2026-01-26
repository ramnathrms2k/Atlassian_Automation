#!/bin/bash

# Usage: 
#   cat broadcom_jira_groups_with_members.txt | grep -i "ATL_Apps" | ./generate_audit_actions.sh

# Define Output Files
FILE_DELETE="action_DELETE_empty_groups.csv"
FILE_ORPHAN="action_FIX_single_member_groups.csv"
FILE_RISK="action_REVIEW_small_groups.csv"
FILE_OK="audit_log_large_groups.csv"

# Write CSV Headers
echo "Group Name,Owner,Action Required" > "$FILE_DELETE"
echo "Group Name,Owner,The Only Member (Risk),Action Required" > "$FILE_ORPHAN"
echo "Group Name,Owner,Current Members,Count" > "$FILE_RISK"
echo "Group Name,Owner,Member Count" > "$FILE_OK"

echo "---------------------------------------------------------"
echo "Processing Group Data and generating Action Lists..."
echo "---------------------------------------------------------"

awk -F'|' -v f_del="$FILE_DELETE" -v f_orp="$FILE_ORPHAN" -v f_risk="$FILE_RISK" -v f_ok="$FILE_OK" '
BEGIN {
    c_del=0; c_orp=0; c_risk=0; c_ok=0
}
{
    # Clean Variables (Trim spaces)
    gsub(/^ +| +$/, "", $1); name=$1
    gsub(/^ +| +$/, "", $3); owner=$3
    gsub(/ /, "", $4);       count_str=$4
    gsub(/^ +| +$/, "", $5); members=$5

    # Convert count to number
    if (index(count_str, "+") > 0) count=9999; else count=count_str+0

    # --- Logic ---

    # 1. EMPTY GROUPS (Count 0) -> Delete List
    if (count == 0) {
        print name "," owner ",DELETE IMMEDIATELY" >> f_del
        c_del++
    }
    
    # 2. SINGLE MEMBER (Count 1) -> Orphan Risk List
    else if (count == 1) {
        # If the member name contains a comma (unlikely for 1 person but safe to quote), wrap in quotes
        print name "," owner "," members ",ADD BACKUP ADMIN" >> f_orp
        c_orp++
    }

    # 3. SMALL TEAMS (Count 2-3) -> Review List
    else if (count >= 2 && count <= 3) {
        # Wrap members in quotes because they contain commas
        print name "," owner ",\"" members "\"," count >> f_risk
        c_risk++
    }

    # 4. HEALTHY/LARGE GROUPS (Count > 3) -> Log only
    else {
        print name "," owner "," count_str >> f_ok
        c_ok++
    }
}
END {
    print "Processing Complete."
    print "---------------------------------------------------------"
    printf "%-30s : %d\n", "Groups to DELETE (0 members)", c_del
    printf "%-30s : %d\n", "Orphan Risks (1 member)", c_orp
    printf "%-30s : %d\n", "Small Teams (2-3 members)", c_risk
    printf "%-30s : %d\n", "Large Groups (>3 members)", c_ok
    print "---------------------------------------------------------"
    print "Files Generated:"
    print "1. " f_del
    print "2. " f_orp "  <-- HIGH PRIORITY"
    print "3. " f_risk
    print "4. " f_ok
}
'
