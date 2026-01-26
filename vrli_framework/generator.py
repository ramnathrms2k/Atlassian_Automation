import json
import re
import argparse
import sys

def escape_for_python(regex_str):
    """
    Helps ensure backslashes are preserved for copy-pasting into Python code.
    """
    if not regex_str:
        return ""
    # We don't want to over-escape, but we want to ensure it looks right in the file
    return regex_str

def generate_entry(data_str):
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"[-] Invalid JSON provided: {e}")
        return

    # Check if this is the standard vRLI Query result JSON
    extracted_fields = data.get("extractedFields", [])
    
    if not extracted_fields:
        print("[-] No 'extractedFields' definition found in this JSON.")
        print("    Tip: Grab the JSON from the 'Request/Response' debug tab in vRLI UI.")
        return

    print("\n# --- COPY BELOW THIS LINE INTO config.py ---\n")

    for field in extracted_fields:
        name = field.get("displayName")
        internal_name = field.get("internalName")
        
        # Get the components
        pre = field.get("preContext", "")
        post = field.get("postContext", "")
        # vRLI uses 'regexValue' for the capture group
        core = field.get("regexValue", ".*")
        
        # Build the Python Client-Side Regex (pyRegex)
        # We combine Pre + Capture(Core) + Post
        # We add (?P<val>...) to capture the actual value
        py_regex = f"{pre}(?P<val>{core}){post}"

        print(f'    "{name}": {{')
        print(f'        "regexPreset": "CUSTOM",')
        print(f'        "preContext": r"{pre}",')
        print(f'        "postContext": r"{post}",')
        print(f'        "customRegex": r"{core}",')
        print(f'        "pyRegex": r"{py_regex}"')
        print(f'    }},')

    print("\n# --- END COPY ---\n")

if __name__ == "__main__":
    print("vRLI Config Generator")
    print("Paste the JSON snippet containing 'extractedFields' (Press Ctrl+D when done):")
    # Read multi-line input
    try:
        user_input = sys.stdin.read()
        generate_entry(user_input)
    except KeyboardInterrupt:
        pass
