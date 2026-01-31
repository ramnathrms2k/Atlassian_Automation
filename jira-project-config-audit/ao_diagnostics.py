import mysql.connector
import configparser
import argparse
import sys

def get_args():
    parser = argparse.ArgumentParser(description="Jira AO Table Diagnostic Tool")
    parser.add_argument("--instance", required=True, help="Instance name from config.ini (e.g., SBX)")
    return parser.parse_args()

def run_diagnostics():
    args = get_args()
    config = configparser.ConfigParser()
    config.read('config.ini')

    if args.instance not in config:
        print(f"Error: Instance '{args.instance}' not found in config.ini")
        sys.exit(1)

    section = config[args.instance]
    
    try:
        conn = mysql.connector.connect(
            host=section['host'], user=section['user'],
            password=section['password'], database=section['database'],
            port=section.getint('port', 3306)
        )
        cursor = conn.cursor(dictionary=True)

        print(f"\n--- Starting Diagnostics for {args.instance} ---")
        
        # 1. Check current Database and User context
        cursor.execute("SELECT DATABASE(), USER()")
        context = cursor.fetchone()
        print(f"Connected as: {context['USER()']} to Database: {context['DATABASE()']}")

        # 2. Broad search for ANY table starting with AO_
        print("\nScanning for all Active Object (AO) tables...")
        cursor.execute("SHOW TABLES LIKE 'AO_%'")
        ao_tables = cursor.fetchall()
        
        if ao_tables:
            print(f"Found {len(ao_tables)} AO tables. Here are the first 10:")
            for row in list(ao_tables)[:10]:
                print(f" - {list(row.values())[0]}")
        else:
            print("!!! No tables starting with 'AO_' were found using SHOW TABLES.")

        # 3. Check INFORMATION_SCHEMA specifically
        print("\nChecking INFORMATION_SCHEMA for Automation or ScriptRunner...")
        query = """
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = %s 
            AND (TABLE_NAME LIKE '%RULE%' OR TABLE_NAME LIKE '%BEHAVIOUR%')
        """
        cursor.execute(query, (section['database'],))
        meta_tables = cursor.fetchall()
        
        if meta_tables:
            print("Found potential matches in INFORMATION_SCHEMA:")
            for row in meta_tables:
                print(f" - {row['TABLE_NAME']}")
        else:
            print("No matches found for 'RULE' or 'BEHAVIOUR' in INFORMATION_SCHEMA.")

    except mysql.connector.Error as err:
        print(f"Database Error: {err}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    run_diagnostics()
