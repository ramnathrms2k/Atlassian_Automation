import mysql.connector
import configparser

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    # Run against SBX as baseline
    s = config['SBX']
    conn = mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'], 
        database=s['database'], port=int(s.get('port', 3306))
    )
    cursor = conn.cursor(dictionary=True)

    # We are looking for where the 'Name' string is stored in this hash
    target_tables = ['ao_33a75d_it_profile', 'ao_33a75d_it_detail', 'ao_33a75d_it_cffield']
    
    print("--- Detailed Schema for Behavior Tables (No Filters) ---")
    for table in target_tables:
        print(f"\nTable: {table}")
        try:
            cursor.execute(f"DESCRIBE {table}")
            for col in cursor.fetchall():
                print(f"  - Column: {col['Field']} ({col['Type']})")
        except Exception as e:
            print(f"  Error: {str(e)}")

    # Search for the string specifically in the Profile table
    print("\n--- Searching Profile Table for Behavior Name ---")
    search_name = "Making RCCA Required field Read only for VCF UBM Projects"
    try:
        cursor.execute("SELECT * FROM ao_33a75d_it_profile WHERE 1=1 LIMIT 5")
        rows = cursor.fetchall()
        if rows:
            print(f"Sample data from ao_33a75d_it_profile: {rows[0]}")
    except: pass

    conn.close()

if __name__ == "__main__":
    main()
