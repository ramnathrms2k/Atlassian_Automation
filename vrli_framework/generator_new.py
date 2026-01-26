import json
import sys

def generate_entry(data_str):
    try:
        data = json.loads(data_str)
    except json.JSONDecodeError as e:
        print(f"[-] Invalid JSON: {e}"); return

    extracted_fields = data.get("extractedFields", [])
    if not extracted_fields:
        print("[-] No 'extractedFields' found."); return

    print("\n# --- COPY BELOW THIS LINE INTO config.py ---\n")

    for field in extracted_fields:
        name = field.get("displayName")
        pre = field.get("preContext", "")
        post = field.get("postContext", "")
        core = field.get("regexValue", ".*")
        
        # Build the Python Regex
        py_regex_inner = f"{pre}(?P<val>{core}){post}"

        # SMART QUOTING LOGIC
        # If the regex contains a double quote, wrap it in single quotes.
        # Otherwise, default to double quotes.
        def smart_quote(s):
            if '"' in s and "'" not in s:
                return f"r'{s}'"
            return f'r"{s}"'

        print(f'    "{name}": {{')
        print(f'        "regexPreset": "CUSTOM",')
        print(f'        "preContext": {smart_quote(pre)},')
        print(f'        "postContext": {smart_quote(post)},')
        print(f'        "customRegex": {smart_quote(core)},')
        print(f'        "pyRegex": {smart_quote(py_regex_inner)}')
        print(f'    }},')

    print("\n# --- END COPY ---\n")

if __name__ == "__main__":
    print("vRLI Config Generator (Smart Quotes)")
    print("Paste JSON (Ctrl+D to finish):")
    try: generate_entry(sys.stdin.read())
    except: pass
