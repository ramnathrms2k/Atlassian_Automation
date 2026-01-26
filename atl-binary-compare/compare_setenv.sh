#!/bin/bash

# ==============================================================================
# Script Name: compare_setenv.sh
# Description: Compares setenv.sh between two versions of Jira or Confluence.
#              Downloads tarballs, extracts only the config file, and diffs.
# Usage:       ./compare_setenv.sh <product> <version1> <version2>
# Example:     ./compare_setenv.sh jira 10.3.12 10.3.15
# ==============================================================================

# --- Configuration ---
TEMP_DIR=$(mktemp -d -t atlassian_compare)
JIRA_BASE_URL="https://product-downloads.atlassian.com/software/jira/downloads"
CONF_BASE_URL="https://product-downloads.atlassian.com/software/confluence/downloads"

# --- Styling ---
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# --- Cleanup Trap ---
cleanup() {
    echo -e "\n${BLUE}--> Cleaning up temporary files...${NC}"
    rm -rf "$TEMP_DIR"
    echo -e "${GREEN}--> Done.${NC}"
}
trap cleanup EXIT

# --- Input Validation ---
if [ "$#" -ne 3 ]; then
    echo -e "${RED}Error: Invalid arguments.${NC}"
    echo "Usage: $0 <jira|confluence> <source_version> <target_version>"
    echo "Example: $0 jira 10.3.12 10.3.15"
    exit 1
fi

PRODUCT=$1
VER1=$2
VER2=$3

# Set URL and Filename patterns based on product
if [[ "$PRODUCT" == "jira" ]]; then
    URL_TEMPLATE="${JIRA_BASE_URL}/atlassian-jira-software-%s.tar.gz"
    FILE_TEMPLATE="atlassian-jira-software-%s.tar.gz"
elif [[ "$PRODUCT" == "confluence" ]]; then
    URL_TEMPLATE="${CONF_BASE_URL}/atlassian-confluence-%s.tar.gz"
    FILE_TEMPLATE="atlassian-confluence-%s.tar.gz"
else
    echo -e "${RED}Error: Product must be 'jira' or 'confluence'.${NC}"
    exit 1
fi

echo -e "${BOLD}Starting Comparison Task${NC}"
echo "------------------------------------------------"
echo "Product: ${PRODUCT}"
echo "Comparing: v${VER1} vs v${VER2}"
echo "Workspace: ${TEMP_DIR}"
echo "------------------------------------------------"

# --- Function: Fetch and Extract ---
process_version() {
    local version=$1
    local tar_file="${TEMP_DIR}/$(printf "$FILE_TEMPLATE" "$version")"
    local download_url=$(printf "$URL_TEMPLATE" "$version")
    local output_file="${TEMP_DIR}/setenv-${version}.sh"

    echo -e "${BLUE}--> [v${version}] Downloading package...${NC}"
    # curl flags: -L (follow redirects), -f (fail on error), -s (silent), -S (show errors)
    curl -L -f -s -S -o "$tar_file" "$download_url"
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to download version ${version}. Check version number or network.${NC}"
        exit 1
    fi

    echo -e "${BLUE}--> [v${version}] Locating setenv.sh in archive...${NC}"
    # List files in tar, find the path to setenv.sh (handles 'standalone' folder variations)
    local internal_path=$(tar -tf "$tar_file" | grep "/bin/setenv.sh" | head -n 1)

    if [ -z "$internal_path" ]; then
        echo -e "${RED}Could not find setenv.sh in the ${version} package!${NC}"
        exit 1
    fi

    echo -e "${BLUE}--> [v${version}] Extracting setenv.sh...${NC}"
    # Extract only that specific file to the temp dir
    tar -xf "$tar_file" -C "$TEMP_DIR" "$internal_path"
    
    # Flatten path: move from temp/subdir/bin/setenv.sh to temp/setenv-ver.sh
    mv "${TEMP_DIR}/${internal_path}" "$output_file"
}

# --- Execution ---
process_version "$VER1"
process_version "$VER2"

# --- Comparison Report ---
FILE1="${TEMP_DIR}/setenv-${VER1}.sh"
FILE2="${TEMP_DIR}/setenv-${VER2}.sh"

echo -e "\n${BOLD}=== COMPARISON REPORT ===${NC}"

# Check if files are identical first
if cmp -s "$FILE1" "$FILE2"; then
    echo -e "\n${GREEN}✔ SUCCESS: The setenv.sh files are IDENTICAL.${NC}"
    echo "You can safely copy your existing setenv.sh to the new installation."
else
    echo -e "\n${RED}⚠ ATTENTION: Differences found between v${VER1} and v${VER2}.${NC}"
    echo "Review the diff below ( < Source | > Target ):"
    echo "------------------------------------------------"
    # Unified diff with color
    diff -u --color=always "$FILE1" "$FILE2"
    echo "------------------------------------------------"
    echo -e "${BOLD}Recommendation:${NC} Manually apply your customizations to the NEW file."
fi

# Cleanup happens automatically via 'trap'
