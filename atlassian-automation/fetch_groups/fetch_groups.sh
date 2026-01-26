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

echo "Fetching Group Data (Paging enabled)..."
echo "Format: Group Name | Primary (ext/desc) | Owner"
echo "----------------------------------------------------------------"

# Run ldapsearch with Paging enabled to bypass size limits
# -E pr=1000/noprompt: Fetches results in pages of 1000
# -o ldif-wrap=no: Prevents line wrapping
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
        
        for(i=1; i<=NF; i++) {
            # Remove carriage returns
            gsub(/\r/, "", $i)

            # Parse Attributes
            if ($i ~ /^cn:/) {
                split($i, a, ": "); name=a[2]
            }
            if ($i ~ /^description:/) {
                split($i, a, ": "); desc=a[2]
            }
            if ($i ~ /^extensionName:/) {
                split($i, a, ": "); extName=a[2]
            }
            if ($i ~ /^managedBy:/) {
                split($i, a, ": "); raw_owner=a[2]
                # Extract CN=Value from the long DN string
                if (match(raw_owner, /CN=[^,]+/)) {
                    owner=substr(raw_owner, RSTART+3, RLENGTH-3)
                } else {
                    owner=raw_owner
                }
            }
        }

        # Logic: If extensionName exists, use it as Primary. 
        # Otherwise fallback to Description.
        if (extName != "") {
            primary = extName
        } else {
            primary = desc
        }

        print name " | " primary " | " owner
    }
'
