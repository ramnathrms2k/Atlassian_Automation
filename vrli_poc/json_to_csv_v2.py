import json
import csv
import sys
import argparse

def main():
    parser = argparse.ArgumentParser(description="Convert Universal vRLI JSON to CSV")
    parser.add_argument("input_file", help="Input JSON file path")
    parser.add_argument("output_file", help="Output CSV file path")
    args = parser.parse_args()

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"[-] Error reading JSON: {e}")
        sys.exit(1)

    if not isinstance(data, list) or not data:
        print("[-] JSON is empty or not a list.")
        sys.exit(0)

    print(f"[*] Converting {len(data)} records...")

    # 1. Identify all unique fields across all records
    # We start with the base headers
    base_headers = ["datetime", "timestamp", "host", "message"]
    dynamic_headers = set()

    for entry in data:
        extracted = entry.get("extracted_fields", {})
        for key in extracted.keys():
            dynamic_headers.add(key)
    
    # Sort dynamic headers for consistent CSV output
    sorted_dynamic = sorted(list(dynamic_headers))
    
    # Final header list
    final_headers = base_headers + sorted_dynamic

    try:
        with open(args.output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=final_headers, quoting=csv.QUOTE_ALL)
            writer.writeheader()
            
            for entry in data:
                # Prepare row with base data
                row = {
                    "datetime": entry.get("datetime", ""),
                    "timestamp": entry.get("timestamp", ""),
                    "host": entry.get("host", ""),
                    "message": entry.get("message", "")
                }
                
                # Flatten the extracted fields into the row
                extracted = entry.get("extracted_fields", {})
                for key in sorted_dynamic:
                    row[key] = extracted.get(key, "")
                
                writer.writerow(row)
                
        print(f"[+] Done. Saved to {args.output_file}")
        print(f"    Included extra columns: {sorted_dynamic}")

    except Exception as e:
        print(f"[-] Error writing CSV: {e}")

if __name__ == "__main__":
    main()
