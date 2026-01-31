import mysql.connector
import configparser
import argparse
import sys

def get_args():
    parser = argparse.ArgumentParser(description="ScriptRunner Behavior Table Diagnostic Tool")
    parser.add_argument("--instance", required=True, help="Instance name from config.ini")
    return parser.parse_args()

def get_db_connection(config, instance):
    if instance not in config:
        print(f"Error: Instance '{instance}' not found in config.ini")
        sys.exit(1)
    s = config[instance]
    return mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'], 
        database=s['database'], port=s.getint('port', 3306)
    )

def main():
    args = get_args()
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    try:
        conn = get_db_connection(config, args.instance)
        cursor = conn.cursor(dictionary=True)
        
        # The query you requested, expanded for extra context
        query = """
        SELECT TABLE_NAME, COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE COLUMN_NAME IN ('BEHAVIOUR_ID', 'PROJECT_ID', 'PROJECT_KEY') 
        AND TABLE_NAME LIKE 'AO_%'
        ORDER BY TABLE_NAME;
        """
        
        print(f"--- Searching for ScriptRunner Tables in {args.instance} ---")
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("No tables found matching the fingerprints.")
        else:
            # Grouping by table for readability
            tables = {}
            for row in results:
                t = row['TABLE_NAME']
                if t not in tables: tables[t] = []
                tables[t].append(row['COLUMN_NAME'])
            
            for table, cols in tables.items():
                print(f"Table Found: {table} | Columns: {', '.join(cols)}")
                
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

if __name__ == "__main__":
    main()
