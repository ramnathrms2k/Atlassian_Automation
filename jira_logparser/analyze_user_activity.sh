#!/bin/bash

# ========================================================================================
# USER ACTIVITY ANALYSIS SCRIPT FOR DIAGNOSTIC BUNDLES
# ========================================================================================
# Purpose: Extract and analyze user activity from Jira/Confluence diagnostic bundles
#          without extracting the bundles themselves
# 
# Usage: ./analyze_user_activity.sh <USERID> <DATE> [BUNDLE_TYPE]
#        ./analyze_user_activity.sh jd008420 2025-09-12 jira
#        ./analyze_user_activity.sh mo024066 2025-09-14 confluence
# 
# Author: SRE Team
# Version: 1.0
# ========================================================================================

# Check command line arguments
if [ $# -lt 2 ]; then
    echo "Usage: $0 <USERID> <DATE> [BUNDLE_TYPE]"
    echo ""
    echo "Arguments:"
    echo "  USERID      - User ID to analyze (e.g., jd008420)"
    echo "  DATE        - Date in YYYY-MM-DD format (e.g., 2025-09-12)"
    echo "  BUNDLE_TYPE - Optional: 'jira' or 'confluence' (default: both)"
    echo ""
    echo "Examples:"
    echo "  $0 jd008420 2025-09-12"
    echo "  $0 mo024066 2025-09-14 jira"
    echo "  $0 user123 2025-09-15 confluence"
    exit 1
fi

USERID="$1"
userid="$1"
DATE="$2"
BUNDLE_TYPE="${3:-both}"

# Validate date format
if [[ ! "$DATE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
    echo "Error: Date must be in YYYY-MM-DD format"
    exit 1
fi

# Convert date to different formats for matching
DATE_DD_MMM_YYYY=$(date -d "$DATE" +"%d/%b/%Y" 2>/dev/null || date -j -f "%Y-%m-%d" "$DATE" +"%d/%b/%Y" 2>/dev/null || echo "$(echo $DATE | awk -F- '{printf "%02d/%s/%04d", $3, $2, $1}' | sed 's/01/Jan/g; s/02/Feb/g; s/03/Mar/g; s/04/Apr/g; s/05/May/g; s/06/Jun/g; s/07/Jul/g; s/08/Aug/g; s/09/Sep/g; s/10/Oct/g; s/11/Nov/g; s/12/Dec/g')")
DATE_YYYY_MM_DD="$DATE"

echo "=== User Activity Analysis ==="
echo "User ID: $USERID"
echo "Date: $DATE ($DATE_DD_MMM_YYYY)"
echo "Bundle Type: $BUNDLE_TYPE"
echo ""

# Function to analyze Jira access logs
analyze_jira_logs() {
    local bundle_file="$1"
    local userid="$2"
    local date_dd_mmm_yyyy="$3"
    
    echo "--- Analyzing Jira Bundle: $(basename "$bundle_file") ---" >&2
    
    # Extract access log snippet from bundle and analyze
    # Jira access log format: IP REQUEST_ID USERNAME [TIMESTAMP] "REQUEST" STATUS SIZE TIME USER_AGENT REQUEST_ID
    # We need: timestamp, username, URI, response time (TIME field)
    
    tar -xzf "$bundle_file" -O --wildcards "*/access_log_snippet.log" 2>/dev/null | \
    awk -v userid="$userid" -v target_date="$date_dd_mmm_yyyy" '
    {
        # Jira format: IP REQUEST_ID USERNAME [TIMESTAMP] "REQUEST" STATUS SIZE TIME USER_AGENT REQUEST_ID
        username = $3;
        timestamp = $4;
        request = $5;
        response_time = $11;  # Response time is in field 11
        
        # Clean up timestamp (remove brackets)
        gsub(/^\[/, "", timestamp);
        gsub(/\]$/, "", timestamp);
        
        # Clean up request (remove quotes)
        gsub(/^"/, "", request);
        gsub(/"$/, "", request);
        
        # Check if this is the target user and date
        if (username == userid && index(timestamp, target_date) > 0) {
            # Extract URI from request (remove method and HTTP version)
            uri = request;
            gsub(/^[A-Z]+ /, "", uri);
            gsub(/ HTTP\/[0-9.]+$/, "", uri);
            
            # Store the data
            print timestamp, username, uri, response_time "ms";
        }
    }' | sort -u
}

# Function to analyze Confluence access logs
analyze_confluence_logs() {
    local bundle_file="$1"
    local userid="$2"
    local date_dd_mmm_yyyy="$3"
    
    echo "--- Analyzing Confluence Bundle: $(basename "$bundle_file") ---" >&2
    
    # Extract access log snippet from bundle and analyze
    # Confluence access log format: IP USER_ID [TIMESTAMP] "REQUEST" STATUS SIZE TIME USER_AGENT
    
    # Extract and process Confluence access logs using simple grep + awk + sed pipeline
    # Confluence format: [TIMESTAMP] USERNAME THREAD IP METHOD REQUEST PROTOCOL STATUS RESPONSE_TIME SIZE REFERER USER_AGENT
    local raw_data=$(tar -xzf "$bundle_file" -O --wildcards "*/access_log_snippet.log" 2>/dev/null)
    local filtered_data=$(echo "$raw_data" | grep "^\[.*\] $userid ")
    local extracted_data=$(echo "$filtered_data" | sed 's/^\[\([^]]*\)\] \([^ ]*\) [^ ]* [^ ]* [^ ]* \([^ ]*\) [^ ]* [^ ]* \([^ ]*\) [^ ]*.*$/\1|\2|\3|\4/')
    echo "$extracted_data" | awk -F'|' -v userid="$userid" -v target_date="$date_dd_mmm_yyyy" '
    NF > 0 {
        timestamp = $1;
        username = $2;
        request = $3;
        response_time = $4;
        
        # Check if this is the target user and date
        if (username == userid && index(timestamp, target_date) > 0) {
            # Extract URI from request (remove method and HTTP version)
            uri = request;
            gsub(/^[A-Z]+ /, "", uri);
            gsub(/ HTTP\/[0-9.]+$/, "", uri);
            
            # Remove epoch timestamps from URI (since= and _= parameters)
            gsub(/[?&]since=[0-9]+/, "", uri);
            gsub(/[?&]_=[0-9]+/, "", uri);
            gsub(/[?&]$/, "", uri);  # Remove trailing ? or &
            
            print timestamp, username, uri, response_time;
        }
    }' | sort -u
}

# Function to calculate statistics
calculate_statistics() {
    local data="$1"
    local userid="$2"
    
    if [ -z "$data" ]; then
        echo "No data found for user $userid"
        return
    fi
    
    # Count total requests
    total_requests=$(echo "$data" | wc -l)
    
    # Extract response times and calculate statistics
    response_times=$(echo "$data" | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+ms$/) print $i}' | sed 's/ms$//' | sort -n)
    
    if [ -z "$response_times" ]; then
        echo "No response time data found"
        return
    fi
    
    # Calculate average
    average_time=$(echo "$response_times" | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')
    
    # Calculate 90th percentile
    total_lines=$(echo "$response_times" | wc -l)
    percentile_90_line=$(( (total_lines * 90) / 100 ))
    if [ $percentile_90_line -eq 0 ]; then
        percentile_90_line=1
    fi
    percentile_90_time=$(echo "$response_times" | sed -n "${percentile_90_line}p")
    
    # Calculate min and max
    min_time=$(echo "$response_times" | head -1 | tr -d ' ')
    max_time=$(echo "$response_times" | tail -1 | tr -d ' ')
    
    # Handle empty min/max
    [ -z "$min_time" ] && min_time="N/A"
    [ -z "$max_time" ] && max_time="N/A"
    
    echo "=== Statistics for User: $userid ==="
    echo "Total Requests: $total_requests"
    echo "Average Response Time: $(printf "%.2f" "$average_time") ms"
    echo "90th Percentile: $percentile_90_time ms"
    echo "Min Response Time: $min_time ms"
    echo "Max Response Time: $max_time ms"
    echo ""
    
    # Show sample of activities
    echo "=== Sample Activities (first 10) ==="
    echo "$data" | head -10 | while read line; do
        echo "  $line"
    done
    echo ""
}

# Main execution
echo "Searching for diagnostic bundles..."

# Find bundles for the specified date
if [ "$BUNDLE_TYPE" = "jira" ] || [ "$BUNDLE_TYPE" = "both" ]; then
    DATE_NO_DASH=$(echo "$DATE_YYYY_MM_DD" | sed 's/-//g')
    JIRA_BUNDLES=$(find . -name "*jira*${DATE_YYYY_MM_DD}*.tar.gz" -o -name "*jira*${DATE_NO_DASH}*.tar.gz" 2>/dev/null)
    
    if [ -n "$JIRA_BUNDLES" ]; then
        echo "Found Jira bundles:"
        echo "$JIRA_BUNDLES"
        echo ""
        
        all_jira_data=""
        for bundle in $JIRA_BUNDLES; do
            bundle_data=$(analyze_jira_logs "$bundle" "$userid" "$DATE_DD_MMM_YYYY")
            if [ -n "$bundle_data" ]; then
                all_jira_data="$all_jira_data
$bundle_data"
            fi
        done
        
        if [ -n "$all_jira_data" ]; then
            calculate_statistics "$all_jira_data" "$userid"
        else
            echo "No Jira data found for user $userid on $DATE"
        fi
    else
        echo "No Jira bundles found for date $DATE"
    fi
fi

if [ "$BUNDLE_TYPE" = "confluence" ] || [ "$BUNDLE_TYPE" = "both" ]; then
    DATE_NO_DASH=$(echo "$DATE_YYYY_MM_DD" | sed 's/-//g')
    CONFLUENCE_BUNDLES=$(find . -name "*confluence*${DATE_YYYY_MM_DD}*.tar.gz" -o -name "*confluence*${DATE_NO_DASH}*.tar.gz" 2>/dev/null)
    
    if [ -n "$CONFLUENCE_BUNDLES" ]; then
        echo "Found Confluence bundles:"
        echo "$CONFLUENCE_BUNDLES"
        echo ""
        
        all_confluence_data=""
        for bundle in $CONFLUENCE_BUNDLES; do
            bundle_data=$(analyze_confluence_logs "$bundle" "$userid" "$DATE_DD_MMM_YYYY")
            if [ -n "$bundle_data" ]; then
                all_confluence_data="$all_confluence_data
$bundle_data"
            fi
        done
        
        if [ -n "$all_confluence_data" ]; then
            calculate_statistics "$all_confluence_data" "$userid"
        else
            echo "No Confluence data found for user $userid on $DATE"
        fi
    else
        echo "No Confluence bundles found for date $DATE"
    fi
fi

echo "=== Analysis Complete ==="
