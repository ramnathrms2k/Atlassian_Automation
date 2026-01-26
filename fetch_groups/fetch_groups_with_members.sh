#!/bin/bash

# Source the configuration
CONFIG_FILE="ldap_config.cfg"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
else
    echo "Error: Configuration file $CONFIG_FILE not found."
    exit 1
fi

# Secure Password Prompt
if [ -z "$LDAP_PASS" ]; then
    echo "Connecting as: $LDAP_BIND_DN"
    read -s -p "Enter LDAP Password: " LDAP_PASS
    echo ""
fi

# We need 'member' to count and extract names
LDAP_ATTRS="cn managedBy description extensionName member"

echo "Fetching Group Data (Paging enabled)..."
echo "Format: Group Name | Primary | Owner | Count | Members (if <= 3)"
echo "---------------------------------------------------------------------------------------"

# Run ldapsearch
# -E pr=1000/noprompt: Fetches groups in pages of 1000
LDAPTLS_REQCERT=never ldapsearch \
    -E pr=1000/noprompt \
    -H "ldaps://${LDAP_HOST}:${LDAP_PORT}" \
    -D "$LDAP_BIND_DN" \
    -w "$LDAP_PASS" \
    -b "$LDAP_BASE_DN" \
    -s sub \
    -o ldif-wrap=no \
    -LLL \
    "$LDAP_FILTER" \
    $LDAP_ATTRS | \
awk '
    BEGIN { 
        RS=""  # Paragraph mode
        FS="\n" 
    }
    {
        name="N/A"
        owner="N/A"
        desc="N/A"
        extName=""
        mem_count=0
        is_large=""
        
        # Reset member string for this record
        mem_list_str=""
        
        for(i=1; i<=NF; i++) {
            # Remove carriage returns
            gsub(/\r/, "", $i)

            # Capture Group Name
            if ($i ~ /^cn:/) {
                split($i, a, ": "); name=a[2]
            }
            # Capture Description
            if ($i ~ /^description:/) {
                split($i, a, ": "); desc=a[2]
            }
            # Capture Extension Name
            if ($i ~ /^extensionName:/) {
                split($i, a, ": "); extName=a[2]
            }
            # Capture Owner
            if ($i ~ /^managedBy:/) {
                split($i, a, ": "); raw_owner=a[2]
                if (match(raw_owner, /CN=[^,]+/)) {
                    owner=substr(raw_owner, RSTART+3, RLENGTH-3)
                } else {
                    owner=raw_owner
                }
            }
            
            # Member Logic
            if ($i ~ /^member.*:/) {
                mem_count++
                
                # Only capture names if we have found fewer than 4 so far
                # (Optimization: dont store strings for groups with 1000 users)
                if (mem_count <= 3) {
                    split($i, m, ": "); raw_mem=m[2]
                    # Extract CN=Name from DN
                    if (match(raw_mem, /CN=[^,]+/)) {
                        mem_name=substr(raw_mem, RSTART+3, RLENGTH-3)
                    } else {
                        mem_name="Unknown"
                    }
                    
                    # Append to list (comma separated)
                    if (mem_list_str == "") {
                        mem_list_str = mem_name
                    } else {
                        mem_list_str = mem_list_str ", " mem_name
                    }
                }
            }
            
            # Detect Range Retrieval (indicating 1500+ members)
            if ($i ~ /^member;range=/) {
                is_large="+"
            }
        }

        # Logic: Primary Fallback
        if (extName != "") {
            primary = extName
        } else {
            primary = desc
        }

        # Logic: Member Column
        # Only print member names if count is between 1 and 3
        if (mem_count >= 1 && mem_count <= 3 && is_large == "") {
            final_mem_col = mem_list_str
        } else {
            final_mem_col = "N/A"
        }

        # Output
        print name " | " primary " | " owner " | " mem_count is_large " | " final_mem_col
    }
'
