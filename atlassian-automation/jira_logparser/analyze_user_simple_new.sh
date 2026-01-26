#!/bin/bash

# ========================================================================================
# SIMPLE USER ACTIVITY ANALYSIS SCRIPT
# ========================================================================================
# Purpose: Extract user activity from diagnostic bundles without extraction
# 
# Usage: ./analyze_user_simple.sh <USERID> <DATE> [BUNDLE_TYPE] [URI_PATTERN]
# 
# Author: SRE Team
# Version: 1.0
# ========================================================================================

if [ $# -lt 2 ]; then
    echo "Usage: $0 <USERID> <DATE> [BUNDLE_TYPE] [URI_PATTERN]"
    echo "Examples:"
    echo "  $0 jd008420 2025-09-12"
    echo "  $0 mo024066 2025-09-14 jira"
    echo "  $0 user123 2025-09-15 confluence"
    echo "  $0 user123 2025-09-15 jira '/rest/api/2/issue'"
    echo "  $0 user123 2025-09-15 confluence '/rest/api/content'"
    echo ""
    echo "URI_PATTERN: Optional regex pattern to filter specific URIs (e.g., '/rest/api/2/issue', '/rest/api/content')"
    exit 1
fi

USERID="$1"
userid="$1"
DATE="$2"
BUNDLE_TYPE="${3:-both}"
URI_PATTERN="${4:-}"

# Convert date formats
DATE_DD_MMM_YYYY=$(date -d "$DATE" +"%d/%b/%Y" 2>/dev/null || date -j -f "%Y-%m-%d" "$DATE" +"%d/%b/%Y" 2>/dev/null || echo "$(echo $DATE | awk -F- '{printf "%02d/%s/%04d", $3, $2, $1}' | sed 's/01/Jan/g; s/02/Feb/g; s/03/Mar/g; s/04/Apr/g; s/05/May/g; s/06/Jun/g; s/07/Jul/g; s/08/Aug/g; s/09/Sep/g; s/10/Oct/g; s/11/Nov/g; s/12/Dec/g')")

echo "=== User Activity Analysis ==="
echo "User ID: $USERID"
echo "Date: $DATE ($DATE_DD_MMM_YYYY)"
echo "Bundle Type: $BUNDLE_TYPE"
echo ""

# Function to analyze Jira logs
analyze_jira() {
    local bundle="$1"
    local userid="$2"
    local uri_pattern="$3"
    echo "--- Analyzing Jira Bundle: $(basename "$bundle") ---" >&2
    
    # Extract and process Jira access logs
    # Jira format: IP REQUEST_ID USERNAME [TIMESTAMP] "REQUEST" STATUS SIZE TIME USER_AGENT REQUEST_ID
    tar -xzf "$bundle" -O --wildcards "*/access_log_snippet.log" 2>/dev/null | \
    awk -v userid="$userid" -v target_date="$DATE_DD_MMM_YYYY" -v uri_pattern="$uri_pattern" '
    {
        # Jira format: IP REQUEST_ID USERNAME [TIMESTAMP] "REQUEST" STATUS SIZE TIME REFERER USER_AGENT SESSION_ID
        username = $3;
        timestamp = $4 " " $5;  # Combine timestamp fields
        uri = $7;  # URI is in field 7
        response_time = $11;  # Response time is in field 11
        
        # Clean up timestamp (remove brackets)
        gsub(/^\[/, "", timestamp);
        gsub(/\]$/, "", timestamp);
        
        # Check if this is the target user and date
        if (username == userid && index(timestamp, target_date) > 0) {
            # Apply URI pattern filter if provided
            if (uri_pattern == "" || uri ~ uri_pattern) {
                if (response_time ~ /^[0-9]+$/) {
                    print timestamp, username, uri, response_time "ms";
                }
            }
        }
    }'
}

# Function to analyze Confluence logs  
analyze_confluence() {
    local bundle="$1"
    local userid="$2"
    local uri_pattern="$3"
    echo "--- Analyzing Confluence Bundle: $(basename "$bundle") ---" >&2
    
    # Extract and process Confluence access logs using simple grep + awk + sed pipeline
    # Confluence format: [TIMESTAMP] USERNAME THREAD IP METHOD REQUEST PROTOCOL STATUS RESPONSE_TIME SIZE REFERER USER_AGENT
    local raw_data=$(tar -xzf "$bundle" -O --wildcards "*/access_log_snippet.log" 2>/dev/null)
    local filtered_data=$(echo "$raw_data" | grep "^\[.*\] $userid ")
    local extracted_data=$(echo "$filtered_data" | sed 's/^\[\([^]]*\)\] \([^ ]*\) [^ ]* [^ ]* [^ ]* \([^ ]*\) [^ ]* [^ ]* \([^ ]*\) [^ ]*.*$/\1|\2|\3|\4/')
    local output=$(echo "$extracted_data" | awk -F'|' -v userid="$userid" -v target_date="$DATE_DD_MMM_YYYY" -v uri_pattern="$uri_pattern" '
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
            
            # Apply URI pattern filter if provided
            if (uri_pattern == "" || uri ~ uri_pattern) {
                print timestamp, username, uri, response_time;
            }
        }
    }')
    
    echo "$output"
}

# Function to calculate statistics
calc_stats() {
    local data="$1"
    local userid="$2"
    local system="$3"
    
    if [ -z "$data" ]; then
        echo "No $system data found for user $userid"
        return
    fi
    
    local total=$(echo "$data" | wc -l)
    # Extract response times that end with 'ms'
    local times=$(echo "$data" | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+ms$/) print $i}' | sed 's/ms$//' | sort -n)
    
    
    if [ -z "$times" ]; then
        echo "No response time data found for $system"
        return
    fi
    
    # Calculate average
    local avg=$(echo "$times" | awk '{sum+=$1; count++} END {if(count>0) print sum/count; else print 0}')
    
    # Calculate 90th percentile
    local total_lines=$(echo "$times" | wc -l)
    local p90_line=$(( (total_lines * 90) / 100 ))
    [ $p90_line -eq 0 ] && p90_line=1
    local p90=$(echo "$times" | sed -n "${p90_line}p")
    
    local min=$(echo "$times" | head -1 | tr -d ' ')
    local max=$(echo "$times" | tail -1 | tr -d ' ')
    
    # Handle empty min/max
    [ -z "$min" ] && min="N/A"
    [ -z "$max" ] && max="N/A"
    
    echo "=== $system Statistics for User: $userid ==="
    echo "Total Requests: $total"
    echo "Average Response Time: $(printf "%.2f" "$avg") ms"
    echo "90th Percentile: $p90 ms"
    echo "Min Response Time: $min ms"
    echo "Max Response Time: $max ms"
    echo ""
    
    echo "=== Sample Activities (first 5) ==="
    echo "$data" | head -5 | while read line; do
        echo "  $line"
    done
    echo ""
}

# Main execution
echo "Searching for diagnostic bundles..."

# Process Jira bundles
if [ "$BUNDLE_TYPE" = "jira" ] || [ "$BUNDLE_TYPE" = "both" ]; then
    DATE_NO_DASH=$(echo "$DATE" | sed 's/-//g')
    JIRA_BUNDLES=$(find . -name "*jira*${DATE}*.tar.gz" -o -name "*jira*${DATE_NO_DASH}*.tar.gz" 2>/dev/null)
    
    if [ -n "$JIRA_BUNDLES" ]; then
        echo "Found Jira bundles:"
        echo "$JIRA_BUNDLES"
        echo ""
        
        all_data=""
        for bundle in $JIRA_BUNDLES; do
            bundle_data=$(analyze_jira "$bundle" "$userid" "$URI_PATTERN")
            [ -n "$bundle_data" ] && all_data="$all_data
$bundle_data"
        done
        
        # Remove duplicates across all bundles before calculating statistics
        unique_data=$(echo "$all_data" | sort -u)
        calc_stats "$unique_data" "$userid" "Jira"
    else
        echo "No Jira bundles found for date $DATE"
    fi
fi

# Process Confluence bundles
if [ "$BUNDLE_TYPE" = "confluence" ] || [ "$BUNDLE_TYPE" = "both" ]; then
    DATE_NO_DASH=$(echo "$DATE" | sed 's/-//g')
    CONFLUENCE_BUNDLES=$(find . -name "*confluence*${DATE}*.tar.gz" -o -name "*confluence*${DATE_NO_DASH}*.tar.gz" 2>/dev/null)
    
    if [ -n "$CONFLUENCE_BUNDLES" ]; then
        echo "Found Confluence bundles:"
        echo "$CONFLUENCE_BUNDLES"
        echo ""
        
        all_data=""
        for bundle in $CONFLUENCE_BUNDLES; do
            bundle_data=$(analyze_confluence "$bundle" "$userid" "$URI_PATTERN")
        [ -n "$bundle_data" ] && all_data="$all_data
$bundle_data"
    done
        # Remove duplicates across all bundles before calculating statistics
        unique_data=$(echo "$all_data" | sort -u)
        calc_stats "$unique_data" "$userid" "Confluence"
    else
        echo "No Confluence bundles found for date $DATE"
    fi
fi

echo "=== Analysis Complete ==="
