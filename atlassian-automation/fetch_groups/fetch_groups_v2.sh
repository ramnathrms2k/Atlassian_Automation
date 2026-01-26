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

# Add 'member' to the requested attributes so we can count them
LDAP_ATTRS="cn managedBy description extensionName member"

echo "Fetching Group Data (Paging enabled)..."
echo "Format: Group Name | Primary (ext/desc) | Owner | Count"
echo "-----------------------------------------------------------------------"

# Run ldapsearch
# -E pr=1000/noprompt: Fetches groups in pages of 1000 to bypass size limit
# -o ldif-wrap=no: Prevents line wrapping for easier parsing
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
        RS=""  # Paragraph mode (each LDAP entry is a record)
        FS="\n" 
    }
    {
        name="N/A"
        owner="N/A"
        desc="N/A"
        extName=""
        mem_count=0
        is_large=""
        
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
            
            # Count Members
            # We look for "member:" OR "member;range=..."
            if ($i ~ /^member.*:/) {
                mem_count++
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

        # Output with count
        print name " | " primary " | " owner " | " mem_count is_large
    }
'
