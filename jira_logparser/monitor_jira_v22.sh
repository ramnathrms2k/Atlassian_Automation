#!/bin/bash

# ========================================================================================
# JIRA PERFORMANCE MONITORING SCRIPT
# ========================================================================================
# Purpose: Comprehensive monitoring of Jira application performance including:
#          - Response time analysis with custom Apdex calculation
#          - System resource utilization (CPU/Memory)
#          - User-specific slow request analysis
#          - Diagnostic bundle generation for troubleshooting
# 
# Author: SRE Team
# Version: 1.0
# Last Updated: $(date +"%Y-%m-%d")
# ========================================================================================

# --- User-configurable variables ---
CURRENT_DATE=$(date +"%Y-%m-%d")
LOG_FILE="/export/jira/logs/access_log.${CURRENT_DATE}"  # Jira access log with current date
APP_LOG_PATH="/export/jirahome/log"                     # Jira application logs directory
DB_SERVER="db-lvnv-it-101.lvn.broadcom.net"            # Jira's database server hostname
NUM_LINES="10000"                                     # Number of log lines to analyze
THRESHOLD_MS="10000"                                    # Threshold for slow request analysis (10 seconds)
REFRESH_INTERVAL="60"                                   # Refresh interval in seconds (for continuous mode)
GENERATE_BUNDLE="${GENERATE_BUNDLE:-true}"             # Set to false for watch mode to improve performance
LOG_ROTATION_BUFFER_MINUTES="${LOG_ROTATION_BUFFER_MINUTES:-5}"  # Minutes after midnight to include previous day's logs
BUNDLE_CONTENT_VALIDATOR="${BUNDLE_CONTENT_VALIDATOR:-true}"     # Set to false to suppress bundle content validation output
# ==================================

# ========================================================================================
# COMMAND LINE ARGUMENT PROCESSING
# ========================================================================================
# Process command line arguments for runtime configuration
# Usage: ./monitor_jira_fixed.sh [--no-validation] [--no-bundle] [--help]
# ========================================================================================
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-validation)
            BUNDLE_CONTENT_VALIDATOR="false"
            echo "Bundle content validation disabled via command line argument"
            shift
            ;;
        --no-bundle)
            GENERATE_BUNDLE="false"
            echo "Bundle generation disabled via command line argument"
            shift
            ;;
        --help)
            echo "Jira Performance Monitoring Script"
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --no-validation    Disable bundle content validation output"
            echo "  --no-bundle        Disable diagnostic bundle generation"
            echo "  --help             Show this help message"
            echo ""
            echo "Environment Variables:"
            echo "  BUNDLE_CONTENT_VALIDATOR=true/false  Control validation output (default: true)"
            echo "  GENERATE_BUNDLE=true/false           Control bundle generation (default: true)"
            echo "  NUM_LINES=10000                      Number of log lines to analyze"
            echo "  THRESHOLD_MS=10000                   Slow request threshold in milliseconds"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Get start time and hostname for file naming
START_TIME=$(date +%s)
HOSTNAME=$(hostname -s)

# ========================================================================================
# LOG ROTATION HANDLING FUNCTION
# ========================================================================================
# Purpose: Intelligently handle log rotation at midnight to prevent data loss
# Logic: During first 5 minutes after midnight, include both previous and current day logs
#        This ensures no data is lost during the log rotation window
# ========================================================================================
get_log_data() {
    local current_hour=$(date +"%H")
    local current_minute=$(date +"%M")
    local minutes_since_midnight=$((10#$current_hour * 60 + 10#$current_minute))
    
    if [ $minutes_since_midnight -le $LOG_ROTATION_BUFFER_MINUTES ]; then
        # Within buffer period - include both current and previous day's logs
        # Use a more robust date calculation to avoid octal parsing issues
        local prev_date=$(date -d "1 day ago" +"%Y-%m-%d" 2>/dev/null || date -v-1d +"%Y-%m-%d" 2>/dev/null || echo "$(date +%Y-%m-%d | awk -F- '{printf "%04d-%02d-%02d", $1, $2, ($3+0)-1}')")
        local prev_log_file="/export/jira/logs/access_log.${prev_date}"
        
        echo "--- Log Rotation Buffer Active (${minutes_since_midnight} minutes past midnight) ---"
        echo "Including data from both ${prev_date} and ${CURRENT_DATE} log files"
        
        # Get data from both files to ensure complete coverage
        if [ -f "$prev_log_file" ]; then
            # Previous day: get last n lines (correct - we want recent activity from yesterday)
            tail -n "$NUM_LINES" "$prev_log_file"
        fi
        if [ -f "$LOG_FILE" ]; then
            # Current day: get ALL lines (not just last n) to avoid missing early entries
            # This is critical because if current day already has >n requests, 
            # tail -n would miss the first few lines of the current day
            cat "$LOG_FILE"
        fi
    else
        # Normal operation - current day only, but check if we need previous day for analysis
        if [ "$LOG_ROTATION_BUFFER_MINUTES" -gt 5 ]; then
            # Extended analysis mode - include previous day's logs
            local prev_date=$(date -d "1 day ago" +"%Y-%m-%d" 2>/dev/null || date -v-1d +"%Y-%m-%d" 2>/dev/null || echo "$(date +%Y-%m-%d | awk -F- '{printf "%04d-%02d-%02d", $1, $2, ($3+0)-1}')")
            local prev_log_file="/export/jira/logs/access_log.${prev_date}"
            
            echo "--- Extended Analysis Mode (${LOG_ROTATION_BUFFER_MINUTES} minutes buffer) ---"
            echo "Including data from both ${prev_date} and ${CURRENT_DATE} log files"
            
            # Get data from both files
            if [ -f "$prev_log_file" ]; then
                tail -n "$NUM_LINES" "$prev_log_file"
            fi
            if [ -f "$LOG_FILE" ]; then
                cat "$LOG_FILE"
            fi
        else
            # Standard operation - current day only
            if [ -f "$LOG_FILE" ]; then
                tail -n "$NUM_LINES" "$LOG_FILE"
            fi
        fi
    fi
}

# ========================================================================================
# DIAGNOSTIC BUNDLE GENERATION FUNCTION
# ========================================================================================
# Purpose: Create comprehensive diagnostic bundle for troubleshooting
# Contents: - Filtered application logs matching access log time range
#          - Monitor output (stdout from this script)
#          - Access log snippet (last 100 lines)
#          - Thread dump of Jira process
#          - System metrics (CPU/Memory)
# ========================================================================================
generate_diagnostics_bundle() {
    local monitor_output_file="$1"
    
    # Define file names with timestamp for uniqueness
    CURRENT_TS=$(date +"%Y%m%d%H%M%S")
    BUNDLE_CONTENT_DIR="diagnostics_bundle_${CURRENT_TS}_${HOSTNAME}"
    BUNDLE_NAME="atlassian-jira-applicationlog_${CURRENT_TS}_${HOSTNAME}.tar.gz"
    FULL_PATH="$(pwd)/diagnostics/$BUNDLE_NAME"
    
    # Print the bundle name and path immediately for user reference
    echo "Diagnostic bundle creation in progress."
    echo "Bundle Name: $BUNDLE_NAME"
    echo "Absolute Path: $FULL_PATH"
    
    # Run the bundling process in the background
    (
        TMP_DIR=$(mktemp -d)
        mkdir "$TMP_DIR/$BUNDLE_CONTENT_DIR"
        
        # Filter access logs to get timestamps for app logs
        # Jira access log format: IP REQUEST_ID USERNAME [TIMESTAMP] "REQUEST" STATUS SIZE TIME REFERER USER_AGENT SESSION_ID
        # Timestamp is in field 4: [13/Sep/2025:13:15:56 -0700]
        FIRST_TS=$(get_log_data | head -n 1 | awk '{print $4}' | sed 's/\[//' | sed 's/ -0700\]//')
        LAST_TS=$(get_log_data | tail -n 1 | awk '{print $4}' | sed 's/\[//' | sed 's/ -0700\]//')
        

        if [ -z "$FIRST_TS" ] || [ -z "$LAST_TS" ]; then
            echo "Error: Could not determine first or last timestamp from $LOG_FILE. Skipping log bundling."
            return
        fi
        
        # Validate that we have proper timestamp format
        if [[ ! "$FIRST_TS" =~ [0-9]{2}/[A-Za-z]{3}/[0-9]{4}:[0-9]{2}:[0-9]{2}:[0-9]{2} ]]; then
            echo "Error: Invalid timestamp format detected: '$FIRST_TS'. Expected format: DD/MMM/YYYY:HH:MM:SS"
            return
        fi

        # Convert access log timestamp format [13/Sep/2025:13:15:56] to Jira format 2025-09-13 13:15:56
        # Parse format: DD/MMM/YYYY:HH:MM:SS -> YYYY-MM-DD HH:MM:SS
        FIRST_TS_SED_PATTERN=$(echo "$FIRST_TS" | awk -F'[/:]' '{printf "%s-%s-%s %s:%s:%s", $3, $2, $1, $4, $5, $6}' | sed 's/Sep/09/g')
        LAST_TS_SED_PATTERN=$(echo "$LAST_TS" | awk -F'[/:]' '{printf "%s-%s-%s %s:%s:%s", $3, $2, $1, $4, $5, $6}' | sed 's/Sep/09/g')
        
        # Filter app logs and save to a file
        # Use a more flexible approach - get logs from the same day with a broader time range
        ACCESS_DATE=$(echo "$FIRST_TS" | awk -F'[/:]' '{printf "%s-%s-%s", $3, $2, $1}' | sed 's/Sep/09/g')
        
        # Calculate time range for validation
        FIRST_TIME_ONLY=$(echo "$FIRST_TS_SED_PATTERN" | awk '{print $2}')
        LAST_TIME_ONLY=$(echo "$LAST_TS_SED_PATTERN" | awk '{print $2}')
        echo "Filtering application logs for time range: $FIRST_TIME_ONLY to $LAST_TIME_ONLY"
        
        # Clear the filtered log file before processing
        > "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log"
        
        # Process log files in reverse chronological order (newest first)
        # Add a small delay to ensure current log file has latest entries
        sleep 0.5
        
        # Process log files in chronological order (newest first)
        
        for log_file in $(ls -t "$APP_LOG_PATH"/atlassian-jira.log* 2>/dev/null); do
            if [ -f "$log_file" ]; then
                # Extract time components for more precise matching
                START_TIME_ONLY=$(echo "$FIRST_TS_SED_PATTERN" | awk '{print $2}')
                END_TIME_ONLY=$(echo "$LAST_TS_SED_PATTERN" | awk '{print $2}')
                ACCESS_DATE_ONLY=$(echo "$FIRST_TS_SED_PATTERN" | awk '{print $1}')
                
                
                # Use grep + awk for precise time range filtering
                # Convert times to seconds for proper numerical comparison
                TEMP_MATCHES=$(grep "^$ACCESS_DATE_ONLY" "$log_file" | awk -v start_time="$START_TIME_ONLY" -v end_time="$END_TIME_ONLY" '
                function time_to_seconds(time_str) {
                    split(time_str, parts, ":");
                    return (parts[1]+0) * 3600 + (parts[2]+0) * 60 + (parts[3]+0);
                }
                {
                    # Extract time from Jira log timestamp (format: 2025-09-10 18:28:15,123)
                    if (match($0, /[0-9]{2}:[0-9]{2}:[0-9]{2}/)) {
                        log_time = substr($0, RSTART, RLENGTH);
                        log_seconds = time_to_seconds(log_time);
                        start_seconds = time_to_seconds(start_time);
                        end_seconds = time_to_seconds(end_time);
                        if (log_seconds >= start_seconds && log_seconds <= end_seconds) {
                            print $0;
                        }
                    }
                }')
                
                # Append matches to the filtered log file
                if [ ! -z "$TEMP_MATCHES" ]; then
                    echo "$TEMP_MATCHES" >> "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log"
                fi
                
                # Count lines found in this log file
                LINES_FOUND=$(echo "$TEMP_MATCHES" | wc -l 2>/dev/null || echo "0")
            fi
        done
        
        # Show total lines found across all log files
        TOTAL_FILTERED_LINES=$(wc -l < "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log" 2>/dev/null || echo "0")
        
        # Show summary of filtered logs
        if [ -s "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log" ]; then
            TOTAL_LINES=$(wc -l < "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log")
            
            # Extract time range more accurately - sort the logs by time first
            # Sort the filtered logs by timestamp to get proper time range
            sort -k1,2 "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log" > "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira_sorted.log"
            
            # Extract time range from sorted logs
            FIRST_LOG_TIME=$(head -1 "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira_sorted.log" | awk '{if(match($0, /[0-9]{2}:[0-9]{2}:[0-9]{2}/)) print substr($0, RSTART, RLENGTH)}')
            LAST_LOG_TIME=$(tail -1 "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira_sorted.log" | awk '{if(match($0, /[0-9]{2}:[0-9]{2}:[0-9]{2}/)) print substr($0, RSTART, RLENGTH)}')
            
            # Replace the unsorted file with the sorted one
            mv "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira_sorted.log" "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log"
            
            # Also extract full timestamps for better validation
            FIRST_FILTERED_TS=$(head -n 1 "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log" | awk '{print $1, $2}' | sed 's/,.*//')
            LAST_FILTERED_TS=$(tail -n 1 "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log" | awk '{print $1, $2}' | sed 's/,.*//')
            
            echo "Filtered Jira logs: $TOTAL_LINES lines captured (Time range: $FIRST_LOG_TIME to $LAST_LOG_TIME)"
            echo "Access log range: $START_TIME_ONLY to $END_TIME_ONLY"
            
            # Validate time range alignment
            if [ "$FIRST_LOG_TIME" = "$LAST_LOG_TIME" ]; then
                echo "Warning: Filtered logs show same start and end time - this may indicate a filtering issue"
            fi
            
            # Calculate time span with cross-midnight support
            if [ "$FIRST_LOG_TIME" != "$LAST_LOG_TIME" ]; then
                # Extract full timestamps (date + time) for proper calculation
                FIRST_FULL_TS=$(head -n 1 "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log" | awk '{print $1, $2}' | sed 's/,.*//')
                LAST_FULL_TS=$(tail -n 1 "$TMP_DIR/$BUNDLE_CONTENT_DIR/filtered_jira.log" | awk '{print $1, $2}' | sed 's/,.*//')
                
                # Convert to epoch seconds for accurate calculation
                FIRST_EPOCH=$(date -d "$FIRST_FULL_TS" +%s 2>/dev/null || echo "0")
                LAST_EPOCH=$(date -d "$LAST_FULL_TS" +%s 2>/dev/null || echo "0")
                
                if [ "$FIRST_EPOCH" != "0" ] && [ "$LAST_EPOCH" != "0" ] && [ "$LAST_EPOCH" -gt "$FIRST_EPOCH" ]; then
                    # Calculate time difference in minutes
                    TIME_SPAN_SECONDS=$((LAST_EPOCH - FIRST_EPOCH))
                    TIME_SPAN_MINUTES=$((TIME_SPAN_SECONDS / 60))
                    
                    # Check if it's a cross-midnight scenario
                    FIRST_DATE=$(echo "$FIRST_FULL_TS" | awk '{print $1}')
                    LAST_DATE=$(echo "$LAST_FULL_TS" | awk '{print $1}')
                    
                    if [ "$FIRST_DATE" != "$LAST_DATE" ]; then
                        echo "  Time span: $TIME_SPAN_MINUTES minutes (cross-midnight: $FIRST_LOG_TIME $FIRST_DATE to $LAST_LOG_TIME $LAST_DATE)"
                    else
                        echo "  Time span: $TIME_SPAN_MINUTES minutes"
                    fi
                else
                    # Fallback to simple time calculation if date parsing fails
                    FIRST_SECONDS=$(echo "$FIRST_LOG_TIME" | awk -F: '{print ($1+0)*3600 + ($2+0)*60 + ($3+0)}')
                    LAST_SECONDS=$(echo "$LAST_LOG_TIME" | awk -F: '{print ($1+0)*3600 + ($2+0)*60 + ($3+0)}')
                    TIME_SPAN_MINUTES=$(( (LAST_SECONDS - FIRST_SECONDS) / 60 ))
                    
                    if [ "$TIME_SPAN_MINUTES" -lt 0 ]; then
                        # Negative result indicates cross-midnight, add 24 hours
                        TIME_SPAN_MINUTES=$((TIME_SPAN_MINUTES + 1440))
                        echo "  Time span: $TIME_SPAN_MINUTES minutes (cross-midnight detected)"
                    else
                        echo "  Time span: $TIME_SPAN_MINUTES minutes"
                    fi
                fi
            else
                echo "  Time span: 0 minutes (same start and end time)"
            fi
        else
            echo "Warning: No filtered Jira logs found!"
        fi
        
        # Get Jira's PID and generate a thread dump
        JIRA_PID=$(ps -ef | grep 'org.apache.catalina.startup.Bootstrap start' | grep -v grep | awk '{print $2}')
        if [ ! -z "$JIRA_PID" ]; then
            jstack "$JIRA_PID" > "$TMP_DIR/$BUNDLE_CONTENT_DIR/threaddump.txt"
        fi
        
        # Copy the monitoring output to the bundle
        if [ -f "$monitor_output_file" ] && [ -s "$monitor_output_file" ]; then
            cp "$monitor_output_file" "$TMP_DIR/$BUNDLE_CONTENT_DIR/monitor_output.log"
        else
            echo "Warning: Monitor output file is empty or missing" > "$TMP_DIR/$BUNDLE_CONTENT_DIR/monitor_output.log"
        fi
        
        # Add access log snippet to the bundle
        get_log_data > "$TMP_DIR/$BUNDLE_CONTENT_DIR/access_log_snippet.log"
        
        # Create diagnostics directory and bundle
        mkdir -p "$(pwd)/diagnostics"
        tar -czvf "$FULL_PATH" -C "$TMP_DIR" "$BUNDLE_CONTENT_DIR"
        
        # Clean up the temporary directory
        rm -rf "$TMP_DIR"
    )
}

# ========================================================================================
# BUNDLE CONTENT VALIDATION FUNCTION
# ========================================================================================
# Purpose: Validate bundle contents by showing head/tail of each bundled file
# This helps verify that the diagnostic bundle contains expected data without manual extraction
# ========================================================================================
validate_bundle_contents() {
    local bundle_path="$1"
    
    if [ "$BUNDLE_CONTENT_VALIDATOR" = "true" ]; then
        echo ""
        echo "=== BUNDLE CONTENT VALIDATION ==="
        echo "Bundle: $(basename "$bundle_path")"
        echo ""
        
        # Create temporary directory to extract bundle for validation
        local temp_extract_dir=$(mktemp -d)
        
        # Extract bundle to temporary directory
        if tar -tzf "$bundle_path" >/dev/null 2>&1; then
            tar -xzf "$bundle_path" -C "$temp_extract_dir" >/dev/null 2>&1
            
            # Find the extracted directory
            local extracted_dir=$(find "$temp_extract_dir" -type d -name "diagnostics_bundle_*" | head -1)
            
            if [ -d "$extracted_dir" ]; then
                echo "--- Access Log Snippet (head -5) ---"
                if [ -f "$extracted_dir/access_log_snippet.log" ]; then
                    head -5 "$extracted_dir/access_log_snippet.log"
                else
                    echo "File not found: access_log_snippet.log"
                fi
                echo ""
                
                echo "--- Access Log Snippet (tail -5) ---"
                if [ -f "$extracted_dir/access_log_snippet.log" ]; then
                    tail -5 "$extracted_dir/access_log_snippet.log"
                else
                    echo "File not found: access_log_snippet.log"
                fi
                echo ""
                
                echo "--- Filtered Jira Logs (head -5) ---"
                if [ -f "$extracted_dir/filtered_jira.log" ]; then
                    head -5 "$extracted_dir/filtered_jira.log"
                else
                    echo "File not found: filtered_jira.log"
                fi
                echo ""
                
                echo "--- Filtered Jira Logs (tail -5) ---"
                if [ -f "$extracted_dir/filtered_jira.log" ]; then
                    tail -5 "$extracted_dir/filtered_jira.log"
                else
                    echo "File not found: filtered_jira.log"
                fi
                echo ""
                
                echo "--- Monitor Output (head -10) ---"
                if [ -f "$extracted_dir/monitor_output.log" ]; then
                    head -10 "$extracted_dir/monitor_output.log"
                else
                    echo "File not found: monitor_output.log"
                fi
                echo ""
                
                echo "--- Thread Dump (head -10) ---"
                if [ -f "$extracted_dir/threaddump.txt" ]; then
                    head -10 "$extracted_dir/threaddump.txt"
                else
                    echo "File not found: threaddump.txt"
                fi
                echo ""
                
                echo "--- System Metrics (head -10) ---"
                if [ -f "$extracted_dir/system_metrics.txt" ]; then
                    head -10 "$extracted_dir/system_metrics.txt"
                else
                    echo "File not found: system_metrics.txt"
                fi
                echo ""
                
                # Show file sizes for validation
                echo "--- Bundle File Sizes ---"
                ls -lh "$extracted_dir"/*.log "$extracted_dir"/*.txt 2>/dev/null | awk '{print $5, $9}' | sed 's|.*/||'
                echo ""
            else
                echo "Error: Could not find extracted bundle directory"
            fi
            
            # Clean up temporary extraction directory
            rm -rf "$temp_extract_dir"
        else
            echo "Error: Could not extract bundle for validation"
        fi
        
        echo "=== END BUNDLE CONTENT VALIDATION ==="
        echo ""
    fi
}

# Get all monitoring output and redirect to a temporary file
TMP_OUTPUT=$(mktemp)

(
    # --- Jira Monitoring Dashboard on $HOSTNAME ---
    echo "--- Jira Monitoring Dashboard on $HOSTNAME ---"
    echo ""
    
    # --- App Server Load and Memory ---
    echo "--- App Server Load and Memory ---"
    uptime | awk -F'load average:' '{print $2}'
    echo ""
    echo "Memory Usage:"
    free -m
    echo ""

    # --- DB Server Load and Memory ---
    echo "--- DB Server Load and Memory ($DB_SERVER) ---"
    ssh -t "$DB_SERVER" 'uptime | awk -F"load average:" "{print \$2}"' 2>/dev/null | grep -v "Authenticated" | grep -v "Connection" | grep -v "Transferred"
    echo ""
    ssh -t "$DB_SERVER" 'free -m' 2>/dev/null | grep -v "Authenticated" | grep -v "Connection" | grep -v "Transferred"
    echo ""

    # ========================================================================================
    # TIME BUCKET ANALYSIS
    # ========================================================================================
    # Purpose: Categorize response times into buckets for performance analysis
    # Custom Apdex Logic (T=5s):
    #   - Satisfied: 0-5 seconds (0-1s + 1-5s buckets)
    #   - Tolerating: 5-30 seconds (5-10s + 10-30s buckets)  
    #   - Frustrated: >30 seconds (30-60s + 1-5min + >5min buckets)
    # Note: This custom logic is tailored for complex Jira operations
    # ========================================================================================
    echo "--- Time Bucket Analysis ---"
    get_log_data | \
    awk '
    {
        time_taken = $11 + 0;   # Extract response time from 11th field (milliseconds)
        if (time_taken >= 0) {
            # Categorize response times into predefined buckets
            if (time_taken <= 1000) { bucket["0_1000"]++; }           # 0-1s (Satisfied)
            else if (time_taken <= 5000) { bucket["1000_5000"]++; }   # 1-5s (Satisfied)
            else if (time_taken <= 10000) { bucket["5000_10000"]++; } # 5-10s (Tolerating)
            else if (time_taken <= 30000) { bucket["10000_30000"]++; }# 10-30s (Tolerating)
            else if (time_taken <= 60000) { bucket["30000_60000"]++; }# 30-60s (Frustrated)
            else if (time_taken <= 300000) { bucket["60000_300000"]++; }# 1-5min (Frustrated)
            else { bucket["300000"]++; }                              # >5min (Frustrated)
            total_requests++;
        }
    }
    END {
        buckets["0_1000"]=bucket["0_1000"]+0; buckets["1000_5000"]=bucket["1000_5000"]+0;
        buckets["5000_10000"]=bucket["5000_10000"]+0; buckets["10000_30000"]=bucket["10000_30000"]+0;
        buckets["30000_60000"]=bucket["30000_60000"]+0; buckets["60000_300000"]=bucket["60000_300000"]+0;
        buckets["300000"]=bucket["300000"]+0;

        printf "%-20s | %-8s | %-9s\n", "Time Bucket (ms)", "Count", "% of Total";
        printf "%-20s | %-8s | %-9s\n", "====================", "========", "=========";
        printf "%-20s | %-8s | %-9s\n", "0-1s (Satisfied)", buckets["0_1000"], sprintf("%.2f%%", buckets["0_1000"]/total_requests*100);                                                                             
        printf "%-20s | %-8s | %-9s\n", "1-5s (Satisfied)", buckets["1000_5000"], sprintf("%.2f%%", buckets["1000_5000"]/total_requests*100);                                                                       
        printf "%-20s | %-8s | %-9s\n", "5-10s (Tolerating)", buckets["5000_10000"], sprintf("%.2f%%", buckets["5000_10000"]/total_requests*100);                                                                    
        printf "%-20s | %-8s | %-9s\n", "10-30s (Tolerating)", buckets["10000_30000"], sprintf("%.2f%%", buckets["10000_30000"]/total_requests*100);                                                                
        printf "%-20s | %-8s | %-9s\n", "30-60s (Frustrated)", buckets["30000_60000"], sprintf("%.2f%%", buckets["30000_60000"]/total_requests*100);                                                                
        printf "%-20s | %-8s | %-9s\n", "1-5min (Frustrated)", buckets["60000_300000"], sprintf("%.2f%%", buckets["60000_300000"]/total_requests*100);                                                              
        printf "%-20s | %-8s | %-9s\n", ">5min (Frustrated)", buckets["300000"], sprintf("%.2f%%", buckets["300000"]/total_requests*100);
    }'
    echo ""

    # ========================================================================================
    # APDEX SCORE CALCULATION
    # ========================================================================================
    # Purpose: Calculate Application Performance Index (Apdex) for user satisfaction measurement
    # Custom Thresholds (T=5s for complex Jira operations):
    #   - Satisfied: ≤5,000ms (5 seconds) - Excellent user experience
    #   - Tolerating: 5,001-30,000ms (5-30 seconds) - Acceptable but not ideal
    #   - Frustrated: >30,000ms (>30 seconds) - Poor user experience
    # Formula: Apdex = (Satisfied + Tolerating/2) / Total Requests
    # Score Range: 0.0 (worst) to 1.0 (best)
    # ========================================================================================
    echo "--- Apdex Score Analysis (T=5s) ---"
    get_log_data | awk '
    {
        time_taken = $11 + 0;   # Extract response time from 11th field
        total_requests++;
        # Apply custom Apdex thresholds for complex Jira operations
        if (time_taken <= 5000) { satisfied_count++; }       # Satisfied: ≤5s
        else if (time_taken <= 30000) { tolerating_count++; }# Tolerating: 5-30s
        else { frustrated_count++; }                         # Frustrated: >30s
    }
    END {
        # Calculate Apdex score using standard formula
        apdex_score = (satisfied_count + (tolerating_count / 2)) / total_requests;
        printf "Apdex Score: %.2f (Total Requests: %d, Satisfied: %d, Tolerating: %d, Frustrated: %d)\n", apdex_score, total_requests, satisfied_count+0, tolerating_count+0, frustrated_count+0;
    }'
    echo ""

    # ========================================================================================
    # RESPONSE TIME STATISTICAL ANALYSIS
    # ========================================================================================
    # Purpose: Provide detailed response time statistics for performance analysis
    # Metrics: Average, 90th percentile, 80th percentile, min, max response times
    # Use Case: Quick performance overview for the analyzed request bucket
    # ========================================================================================
    echo "--- Response Time Statistical Analysis ---"
    get_log_data | awk '
    {
        time_taken = $11 + 0;   # Extract response time from 11th field
        if (time_taken >= 0) {
            times[NR] = time_taken;
            sum += time_taken;
            if (time_taken < min || min == 0) min = time_taken;
            if (time_taken > max) max = time_taken;
            count++;
        }
    }
    END {
        if (count > 0) {
            # Sort times array for percentile calculation
            asort(times);
            
            # Calculate percentiles
            p80_index = int(count * 0.8);
            p90_index = int(count * 0.9);
            p95_index = int(count * 0.95);
            
            # Handle edge cases for percentiles
            if (p80_index < 1) p80_index = 1;
            if (p90_index < 1) p90_index = 1;
            if (p95_index < 1) p95_index = 1;
            if (p80_index > count) p80_index = count;
            if (p90_index > count) p90_index = count;
            if (p95_index > count) p95_index = count;
            
            p80_time = times[p80_index];
            p90_time = times[p90_index];
            p95_time = times[p95_index];
            
            printf "Average Response Time: %.2f ms\n", sum/count;
            printf "95th Percentile: %d ms\n", p95_time;
            printf "90th Percentile: %d ms\n", p90_time;
            printf "80th Percentile: %d ms\n", p80_time;
            printf "Min Response Time: %d ms\n", min;
            printf "Max Response Time: %d ms\n", max;
        } else {
            printf "No valid response time data found\n";
        }
    }'
    echo ""

    # ========================================================================================
    # INDIVIDUAL USER SLOW REQUEST ANALYSIS
    # ========================================================================================
    # Purpose: Identify users experiencing slow requests for targeted troubleshooting
    # Threshold: Requests >10 seconds (configurable via THRESHOLD_MS)
    # Output: Per-user statistics including count, max time, and timestamps
    # Use Case: Identify problematic users and time periods for investigation
    # ========================================================================================
    echo "--- Individual User Request Analysis (>$THRESHOLD_MS ms) ---"
    echo "UserID          | Count | Last Time (ms) | Max Time (ms) | First Timestamp      | Last Timestamp"
    echo "================|=======|================|===============|======================|================"
    get_log_data | \
    awk -v threshold="$THRESHOLD_MS" '
    $11 > threshold {   # Filter requests exceeding threshold (10 seconds)
        count[$3]++;   # Count slow requests per user
        if (max_time[$3] < $11) {
            max_time[$3] = $11;   # Track maximum response time per user
        }
        if (user_first_timestamp[$3] == "") {
            user_first_timestamp[$3] = $4;  # Record first occurrence timestamp
        }
        user_last_timestamp[$3] = $4;  # Update last occurrence timestamp
        user_last_time_taken[$3] = $11;  # Update last response time
        user_max_time[$3] = max_time[$3]; # Store max time for output
    }
    END {
        for (user in count) {
            sub(/\[/, "", user_first_timestamp[user]);
            sub(/\[/, "", user_last_timestamp[user]);
            printf "%-15s | %-5s | %-13s | %-12s | %s | %s\n", user, count[user], user_last_time_taken[user], user_max_time[user], user_first_timestamp[user], user_last_timestamp[user];
        }
    }' | sort -t"|" -k2 -nr
    
) | tee "$TMP_OUTPUT"

# Ensure the file is completely written before proceeding
sync
sleep 0.5

# Only generate bundle if requested
if [ "$GENERATE_BUNDLE" = "true" ]; then
    echo ""
    echo "--- Diagnostic Log Bundle ---"
    generate_diagnostics_bundle "$TMP_OUTPUT"
    
    # Validate bundle contents if enabled
    if [ -f "$(pwd)/diagnostics/atlassian-jira-applicationlog_$(date +"%Y%m%d%H%M%S")_${HOSTNAME}.tar.gz" ]; then
        # Find the most recent bundle file
        BUNDLE_FILE=$(ls -t "$(pwd)/diagnostics"/atlassian-jira-applicationlog_*_${HOSTNAME}.tar.gz 2>/dev/null | head -1)
        if [ -n "$BUNDLE_FILE" ]; then
            validate_bundle_contents "$BUNDLE_FILE"
        fi
    fi
else
    echo ""
    echo "--- Bundle generation skipped (set GENERATE_BUNDLE=true to enable) ---"
fi

# Clean up the output file
rm "$TMP_OUTPUT"

# ========================================================================================
# EXECUTION SUMMARY
# ========================================================================================
# Calculate and display execution time for performance monitoring
END_TIME=$(date +%s)
echo ""
echo "Time to complete: $((END_TIME - START_TIME)) seconds"

# ========================================================================================
# SCRIPT COMPLETION NOTES
# ========================================================================================
# This script provides comprehensive Jira performance monitoring including:
# 1. System resource utilization (CPU/Memory) for both app and database servers
# 2. Response time analysis with custom Apdex calculation tailored for complex operations
# 3. User-specific slow request analysis for targeted troubleshooting
# 4. Diagnostic bundle generation with filtered logs and system metrics
# 
# For production use:
# - Run via cron for automated monitoring (every 2-3 minutes)
# - Use GENERATE_BUNDLE=false for watch mode to improve performance
# - Monitor Apdex scores for user satisfaction trends
# - Investigate users with high slow request counts
# ========================================================================================
