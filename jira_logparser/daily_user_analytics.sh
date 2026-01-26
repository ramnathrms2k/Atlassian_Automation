#!/bin/bash

# ========================================================================================
# DAILY USER ANALYTICS SCRIPT
# ========================================================================================
# Purpose: Analyze user activity from live log files and generate daily statistics
# Usage: ./daily_user_analytics.sh <appname> <userid> [start_date] [end_date]
# 
# Parameters:
#   appname    - Application name: 'jira' or 'conf'
#   userid     - User ID to analyze
#   start_date - Start date (optional, format: YYYY-MM-DD)
#   end_date   - End date (optional, format: YYYY-MM-DD)
#
# Output: CSV format with daily statistics per user
# Columns: date,hostname,userid,request_count,min_response_time,max_response_time,avg_response_time,p90_response_time,p80_response_time
#
# Examples:
#   ./daily_user_analytics.sh jira sd007878
#   ./daily_user_analytics.sh conf sd007878 2025-09-01 2025-09-15
#   ./daily_user_analytics.sh jira sd007878 2025-09-13
# ========================================================================================

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display usage
show_usage() {
    echo "Usage: $0 <appname> <userid> [start_date] [end_date]"
    echo ""
    echo "Parameters:"
    echo "  appname    - Application name: 'jira' or 'conf'"
    echo "  userid     - User ID to analyze"
    echo "  start_date - Start date (optional, format: YYYY-MM-DD)"
    echo "  end_date   - End date (optional, format: YYYY-MM-DD)"
    echo ""
    echo "Examples:"
    echo "  $0 jira sd007878"
    echo "  $0 conf sd007878 2025-09-01 2025-09-15"
    echo "  $0 jira sd007878 2025-09-13"
    echo ""
    echo "Output: CSV format with daily statistics per user"
    echo "Columns: date,hostname,userid,request_count,min_response_time,max_response_time,avg_response_time,p90_response_time,p80_response_time"
}

# Function to validate date format
validate_date() {
    local date_str="$1"
    if [[ ! $date_str =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo -e "${RED}Error: Invalid date format '$date_str'. Use YYYY-MM-DD format.${NC}" >&2
        return 1
    fi
    
    # Check if date is valid (more lenient for future dates)
    if ! date -d "$date_str" >/dev/null 2>&1; then
        # Try with a different approach for future dates
        if ! date -j -f "%Y-%m-%d" "$date_str" >/dev/null 2>&1; then
            echo -e "${RED}Error: Invalid date '$date_str'.${NC}" >&2
            return 1
        fi
    fi
    
    return 0
}

# Function to get hostname without domain
get_hostname() {
    local full_hostname="$1"
    echo "$full_hostname" | cut -d'.' -f1
}

# Function to analyze Jira logs
analyze_jira_logs() {
    local userid="$1"
    local start_date="$2"
    local end_date="$3"
    local log_dir="/export/jira/logs"
    
    # Check if log directory exists
    if [ ! -d "$log_dir" ]; then
        echo -e "${RED}Error: Jira log directory not found: $log_dir${NC}" >&2
        return 1
    fi
    
    # Find available log files (try both with and without .log extension)
    local log_files=($(find "$log_dir" -name "access_log.*" -type f | grep -E "access_log\.[0-9]{4}-[0-9]{2}-[0-9]{2}(\.log)?$" | sort))
    
    if [ ${#log_files[@]} -eq 0 ]; then
        echo -e "${RED}Error: No Jira log files found in $log_dir${NC}" >&2
        return 1
    fi
    
    # Process each log file
    for log_file in "${log_files[@]}"; do
        local log_date=$(basename "$log_file" | sed 's/access_log\.\(.*\)\.log$/\1/' | sed 's/access_log\.\(.*\)$/\1/')
        
        # Check if date is within range
        if [ -n "$start_date" ] && [ "$log_date" \< "$start_date" ]; then
            continue
        fi
        if [ -n "$end_date" ] && [ "$log_date" \> "$end_date" ]; then
            continue
        fi
        
        # Analyze this log file
        analyze_single_log "$log_file" "$userid" "$log_date" "jira"
    done
}

# Function to analyze Confluence logs
analyze_confluence_logs() {
    local userid="$1"
    local start_date="$2"
    local end_date="$3"
    local log_dir="/export/confluence/logs"
    
    # Check if log directory exists
    if [ ! -d "$log_dir" ]; then
        echo -e "${RED}Error: Confluence log directory not found: $log_dir${NC}" >&2
        return 1
    fi
    
    # Find available log files (Confluence uses conf_access_log.*.log pattern)
    local log_files=($(find "$log_dir" -name "conf_access_log.*" -type f | grep -E "conf_access_log\.[0-9]{4}-[0-9]{2}-[0-9]{2}(\.log)?$" | sort))
    
    if [ ${#log_files[@]} -eq 0 ]; then
        echo -e "${RED}Error: No Confluence log files found in $log_dir${NC}" >&2
        return 1
    fi
    
    # Process each log file
    for log_file in "${log_files[@]}"; do
        local log_date=$(basename "$log_file" | sed 's/conf_access_log\.\(.*\)\.log$/\1/' | sed 's/conf_access_log\.\(.*\)$/\1/')
        
        # Check if date is within range
        if [ -n "$start_date" ] && [ "$log_date" \< "$start_date" ]; then
            continue
        fi
        if [ -n "$end_date" ] && [ "$log_date" \> "$end_date" ]; then
            continue
        fi
        
        # Analyze this log file
        analyze_single_log "$log_file" "$userid" "$log_date" "conf"
    done
}

# Function to analyze a single log file
analyze_single_log() {
    local log_file="$1"
    local userid="$2"
    local log_date="$3"
    local app_type="$4"
    
    # Get hostname from log file path or system
    local hostname=$(hostname -s 2>/dev/null || echo "unknown")
    
    # Extract user data based on app type
    local user_data=""
    if [ "$app_type" = "jira" ]; then
        # Jira format: IP REQUEST_ID USERNAME [TIMESTAMP] "REQUEST" STATUS SIZE TIME REFERER USER_AGENT SESSION_ID
        user_data=$(grep " $userid " "$log_file" 2>/dev/null | awk '
        {
            # Extract response time from field 10 (accounting for quoted fields)
            response_time = $10 + 0;
            if (response_time > 0) {
                print response_time;
            }
        }')
    else
        # Confluence format: [TIMESTAMP] USERNAME THREAD IP METHOD REQUEST PROTOCOL STATUS RESPONSE_TIME SIZE REFERER USER_AGENT
        user_data=$(grep " $userid " "$log_file" 2>/dev/null | awk '
        {
            # Extract response time by searching for field ending with "ms" (more robust)
            response_time = 0;
            for(i=1;i<=NF;i++){
                if($i~/[0-9]+ms$/){
                    response_time = $i;
                    gsub(/ms$/, "", response_time);
                    response_time = response_time + 0;
                    break;
                }
            }
            if (response_time > 0) {
                print response_time;
            }
        }')
    fi
    
    # Check if user has any requests - if no data, output zero values for completeness
    if [ -z "$user_data" ]; then
        # Output zero values for days with no data (useful for plotting)
        echo "$log_date,$hostname,$userid,0,0,0,0.00,0,0"
        return
    fi
    
    # Calculate statistics
    local request_count=$(echo "$user_data" | wc -l | tr -d ' ')
    local min_time=$(echo "$user_data" | sort -n | head -1 | tr -d ' ')
    local max_time=$(echo "$user_data" | sort -n | tail -1 | tr -d ' ')
    local avg_time=$(echo "$user_data" | awk '{sum+=$1; count++} END {if(count>0) printf "%.2f", sum/count; else print "0"}')
    
    # Calculate percentiles
    local p80_time=$(echo "$user_data" | sort -n | awk 'BEGIN{i=0} {times[++i]=$1} END {if(i>0) {p80=int(i*0.8); if(p80<1) p80=1; if(p80>i) p80=i; print times[p80]} else print "0"}')
    local p90_time=$(echo "$user_data" | sort -n | awk 'BEGIN{i=0} {times[++i]=$1} END {if(i>0) {p90=int(i*0.9); if(p90<1) p90=1; if(p90>i) p90=i; print times[p90]} else print "0"}')
    
    # Output CSV row
    echo "$log_date,$hostname,$userid,$request_count,$min_time,$max_time,$avg_time,$p90_time,$p80_time"
}

# Main script logic
main() {
    # Check minimum arguments
    if [ $# -lt 2 ]; then
        echo -e "${RED}Error: Missing required arguments${NC}" >&2
        show_usage
        exit 1
    fi
    
    local appname="$1"
    local userid="$2"
    local start_date="$3"
    local end_date="$4"
    
    # Validate appname
    if [ "$appname" != "jira" ] && [ "$appname" != "conf" ]; then
        echo -e "${RED}Error: Invalid appname '$appname'. Use 'jira' or 'conf'${NC}" >&2
        show_usage
        exit 1
    fi
    
    # Validate dates if provided
    if [ -n "$start_date" ] && ! validate_date "$start_date"; then
        exit 1
    fi
    if [ -n "$end_date" ] && ! validate_date "$end_date"; then
        exit 1
    fi
    
    # Validate date range
    if [ -n "$start_date" ] && [ -n "$end_date" ] && [ "$start_date" \> "$end_date" ]; then
        echo -e "${RED}Error: Start date cannot be after end date${NC}" >&2
        exit 1
    fi
    
    # Print CSV header
    echo "date,hostname,userid,request_count,min_response_time_ms,max_response_time_ms,avg_response_time_ms,p90_response_time_ms,p80_response_time_ms"
    
    # Analyze logs based on app type
    if [ "$appname" = "jira" ]; then
        analyze_jira_logs "$userid" "$start_date" "$end_date"
    else
        analyze_confluence_logs "$userid" "$start_date" "$end_date"
    fi
}

# Run main function
main "$@"
