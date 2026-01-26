#!/bin/bash

# Hourly System Analytics Script
# Analyzes Jira and Confluence logs at hourly granularity
# Combines all users per hour for system-wide performance insights

# Configuration
JIRA_LOG_DIR="/export/jira/logs"
CONFLUENCE_LOG_DIR="/export/confluence/logs"
NUM_LINES=10000
THRESHOLD_MS=10000

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
show_usage() {
    echo "Usage: $0 [APP] [START_DATE] [END_DATE]"
    echo ""
    echo "Arguments:"
    echo "  APP         - Application to analyze: 'jira', 'confluence', or 'both' (default: both)"
    echo "  START_DATE  - Start date in YYYY-MM-DD format (optional)"
    echo "  END_DATE    - End date in YYYY-MM-DD format (optional)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Analyze both apps for all available dates"
    echo "  $0 jira                              # Analyze Jira for all available dates"
    echo "  $0 confluence                        # Analyze Confluence for all available dates"
    echo "  $0 both 2025-09-15                  # Analyze both apps for specific date"
    echo "  $0 jira 2025-09-15 2025-09-20       # Analyze Jira for date range"
    echo ""
    echo "Output: CSV format with hourly system-wide metrics"
    echo "Columns: datetime,hostname,app,request_count,min_response_time_ms,max_response_time_ms,avg_response_time_ms,p90_response_time_ms,p80_response_time_ms"
}

# Function to validate date format
validate_date() {
    local date_str="$1"
    if [[ ! $date_str =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
        echo -e "${RED}Error: Invalid date format. Use YYYY-MM-DD${NC}" >&2
        return 1
    fi
    
    # Check if date is valid
    if ! date -d "$date_str" >/dev/null 2>&1; then
        echo -e "${RED}Error: Invalid date: $date_str${NC}" >&2
        return 1
    fi
    
    return 0
}

# Function to get hostname
get_hostname() {
    hostname -s 2>/dev/null || echo "unknown"
}

# Function to analyze Jira logs for a specific hour
analyze_jira_hour() {
    local log_date="$1"
    local hour="$2"
    local log_file="$3"
    
    if [ ! -f "$log_file" ]; then
        return
    fi
    
    # Convert date to DD/MMM/YYYY format for log parsing
    local date_dd_mmm_yyyy=$(date -d "$log_date" '+%d/%b/%Y' 2>/dev/null)
    
    # Extract hour from timestamp and filter for specific hour
    local hour_start=$(printf "%02d:00:00" $hour)
    local hour_end=$(printf "%02d:59:59" $hour)
    
    # Search for specific hour pattern
    local hour_pattern="\[$date_dd_mmm_yyyy:$(printf "%02d" $hour):"
    
    # Parse Jira access logs for the specific hour
    local hour_data=$(grep -E "$hour_pattern" "$log_file" 2>/dev/null | awk '
    {
        # Jira log format: IP JIRA_REQUEST_ID USERNAME [TIMESTAMP] "METHOD URI HTTP_VERSION" STATUS SIZE RESPONSE_TIME "REFERER" "USER_AGENT" "SESSION_ID"
        # Field positions: 1   2               3        4           5                   6       7     8             9          10           11
        
        # Extract fields
        ip = $1
        jira_id = $2
        username = $3
        timestamp = $4 " " $5
        request = $6
        status = $7
        size = $8
        response_time = $11
        referer = $9
        user_agent = $10
        session_id = $12
        
        # Clean up response time (remove quotes if present)
        gsub(/"/, "", response_time)
        
        # Only process if response_time is numeric
        if (response_time ~ /^[0-9]+$/) {
            print response_time
        }
    }' | sort -n)
    
    if [ -n "$hour_data" ]; then
        # Calculate statistics
        local count=$(echo "$hour_data" | wc -l)
        local min=$(echo "$hour_data" | head -n1)
        local max=$(echo "$hour_data" | tail -n1)
        local avg=$(echo "$hour_data" | awk '{sum+=$1; count++} END {if(count>0) printf "%.2f", sum/count; else print "0.00"}')
        local p99=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.99); if(idx<1) idx=1; print sorted[idx]}}')
        local p98=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.98); if(idx<1) idx=1; print sorted[idx]}}')
        local p95=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.95); if(idx<1) idx=1; print sorted[idx]}}')
        local p90=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.9); if(idx<1) idx=1; print sorted[idx]}}')
        local p80=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.8); if(idx<1) idx=1; print sorted[idx]}}')
        
        
        # Output CSV row
        local datetime="${log_date} $(printf "%02d:00" $hour)"
        local hostname=$(get_hostname)
        echo "$datetime,$hostname,jira,$count,$min,$max,$avg,$p99,$p98,$p95,$p90,$p80"
    else
        # Output zero values for missing hours
        local hostname=$(hostname -s 2>/dev/null || echo "unknown")
        echo "$date $(printf "%02d" $hour):00,$hostname,$app,0,0,0,0.00,0,0,0,0,0"
    fi
}

# Function to analyze Confluence logs for a specific hour
analyze_confluence_hour() {
    local log_date="$1"
    local hour="$2"
    local log_file="$3"
    
    if [ ! -f "$log_file" ]; then
        return
    fi
    
    # Convert date to DD/MMM/YYYY format for log parsing
    local date_dd_mmm_yyyy=$(date -d "$log_date" '+%d/%b/%Y' 2>/dev/null)
    
    # Extract hour from timestamp and filter for specific hour
    local hour_start=$(printf "%02d:00:00" $hour)
    local hour_end=$(printf "%02d:59:59" $hour)
    
    # Search for specific hour pattern
    local hour_pattern="\[$date_dd_mmm_yyyy:$(printf "%02d" $hour):"
    
    # Parse Confluence access logs for the specific hour
    local hour_data=$(grep -E "$hour_pattern" "$log_file" 2>/dev/null | awk '
    {
        # Confluence log format: [TIMESTAMP] USERNAME THREAD IP METHOD REQUEST PROTOCOL STATUS RESPONSE_TIME SIZE REFERER USER_AGENT
        # Field positions:       1           2        3      4  5      6        7        8             9     10       11
        
        # Extract fields
        timestamp = $1
        username = $2
        thread = $3
        ip = $4
        method = $5
        request = $6
        protocol = $7
        status = $8
        response_time = 0
        size = $10
        referer = $11
        user_agent = $12
        
        # Extract response time by searching for field ending with "ms" (more robust)
        for(i=1;i<=NF;i++){
            if($i~/[0-9]+ms$/){
                response_time = $i;
                gsub(/ms$/, "", response_time);
                response_time = response_time + 0;
                break;
            }
        }
        
        # Only process if response_time is numeric
        if (response_time > 0) {
            print response_time
        }
    }' | sort -n)
    
    if [ -n "$hour_data" ]; then
        # Calculate statistics
        local count=$(echo "$hour_data" | wc -l)
        local min=$(echo "$hour_data" | head -n1)
        local max=$(echo "$hour_data" | tail -n1)
        local avg=$(echo "$hour_data" | awk '{sum+=$1; count++} END {if(count>0) printf "%.2f", sum/count; else print "0.00"}')
        local p99=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.99); if(idx<1) idx=1; print sorted[idx]}}')
        local p98=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.98); if(idx<1) idx=1; print sorted[idx]}}')
        local p95=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.95); if(idx<1) idx=1; print sorted[idx]}}')
        local p90=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.9); if(idx<1) idx=1; print sorted[idx]}}')
        local p80=$(echo "$hour_data" | awk 'BEGIN{sorted[0]=""} {sorted[NR]=$1} END {if(NR>0) {asort(sorted); idx=int(NR*0.8); if(idx<1) idx=1; print sorted[idx]}}')
        
        
        # Output CSV row
        local datetime="${log_date} $(printf "%02d:00" $hour)"
        local hostname=$(get_hostname)
        echo "$datetime,$hostname,confluence,$count,$min,$max,$avg,$p99,$p98,$p95,$p90,$p80"
    else
        # Output zero values for missing hours
        local hostname=$(hostname -s 2>/dev/null || echo "unknown")
        echo "$date $(printf "%02d" $hour):00,$hostname,$app,0,0,0,0.00,0,0,0,0,0"
    fi
}

# Function to process a single date
process_date() {
    local date="$1"
    local app="$2"
    
    # Convert date to DD/MMM/YYYY format for log parsing
    local date_dd_mmm_yyyy=$(date -d "$date" '+%d/%b/%Y' 2>/dev/null)
    if [ $? -ne 0 ]; then
        echo -e "${RED}Error: Invalid date format: $date${NC}" >&2
        return 1
    fi
    
    # Process Jira if requested
    if [ "$app" = "jira" ] || [ "$app" = "both" ]; then
        # Find Jira log files for this date
        local jira_logs=$(find "$JIRA_LOG_DIR" -name "access_log.$date" -o -name "access_log.$date.log" 2>/dev/null | sort)
        
        # Debug output
        
        if [ -n "$jira_logs" ]; then
            # Process each hour (0-23)
            for hour in {0..23}; do
                for log_file in $jira_logs; do
                    analyze_jira_hour "$date" "$hour" "$log_file"
                done
            done
        else
            echo "Debug: No Jira log files found for date $date" >&2
        fi
    fi
    
    # Process Confluence if requested
    if [ "$app" = "confluence" ] || [ "$app" = "both" ]; then
        # Find Confluence log files for this date
        local confluence_logs=$(find "$CONFLUENCE_LOG_DIR" -name "conf_access_log.$date" -o -name "conf_access_log.$date.log" 2>/dev/null | sort)
        
        # Debug output
        
        if [ -n "$confluence_logs" ]; then
            # Process each hour (0-23)
            for hour in {0..23}; do
                for log_file in $confluence_logs; do
                    analyze_confluence_hour "$date" "$hour" "$log_file"
                done
            done
        else
            echo "Debug: No Confluence log files found for date $date" >&2
        fi
    fi
}

# Function to get all available dates from log files
get_available_dates() {
    local app="$1"
    local dates=""
    
    if [ "$app" = "jira" ] || [ "$app" = "both" ]; then
        # Get dates from Jira logs
        local jira_dates=$(find "$JIRA_LOG_DIR" -name "access_log.*" 2>/dev/null | sed 's/.*access_log\.\([0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}\)\(\.log\)\?$/\1/' | sort -u)
        dates="$dates $jira_dates"
    fi
    
    if [ "$app" = "confluence" ] || [ "$app" = "both" ]; then
        # Get dates from Confluence logs
        local confluence_dates=$(find "$CONFLUENCE_LOG_DIR" -name "conf_access_log.*" 2>/dev/null | sed 's/.*conf_access_log\.\([0-9]\{4\}-[0-9]\{2\}-[0-9]\{2\}\)\(\.log\)\?$/\1/' | sort -u)
        dates="$dates $confluence_dates"
    fi
    
    # Remove duplicates and sort
    echo "$dates" | tr ' ' '\n' | sort -u | tr '\n' ' '
}

# Main execution
main() {
    # Parse arguments
    local app="${1:-both}"
    local start_date="$2"
    local end_date="$3"
    
    # Validate app parameter
    if [ "$app" != "jira" ] && [ "$app" != "confluence" ] && [ "$app" != "both" ]; then
        echo -e "${RED}Error: Invalid app parameter. Use 'jira', 'confluence', or 'both'${NC}" >&2
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
    
    # Check if date range is valid
    if [ -n "$start_date" ] && [ -n "$end_date" ]; then
        if [ "$start_date" \> "$end_date" ]; then
            echo -e "${RED}Error: Start date cannot be after end date${NC}" >&2
            exit 1
        fi
    fi
    
    # Print CSV header
    echo "datetime,hostname,app,request_count,min_response_time_ms,max_response_time_ms,avg_response_time_ms,p99_response_time_ms,p98_response_time_ms,p95_response_time_ms,p90_response_time_ms,p80_response_time_ms"
    
    # Determine dates to process
    local dates_to_process=""
    
    if [ -n "$start_date" ] && [ -n "$end_date" ]; then
        # Date range
        local current_date="$start_date"
        while [ "$current_date" != "$end_date" ]; do
            dates_to_process="$dates_to_process $current_date"
            current_date=$(date -d "$current_date + 1 day" '+%Y-%m-%d')
        done
        # Add the end date
        dates_to_process="$dates_to_process $end_date"
    elif [ -n "$start_date" ]; then
        # Single date
        dates_to_process="$start_date"
    else
        # All available dates
        dates_to_process=$(get_available_dates "$app")
    fi
    
    # Process each date
    for date in $dates_to_process; do
        if [ -n "$date" ]; then
            process_date "$date" "$app"
        fi
    done
}

# Run main function
main "$@"
