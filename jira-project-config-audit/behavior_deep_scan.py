import mysql.connector
import configparser
import argparse

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    s = config['PRD'] # Running against PRD as baseline
    conn = mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'], 
        database=s['database'], port=s.getint('port', 3306)
    )
    cursor = conn.cursor(dictionary=True)

    # 1. Let's find out what columns actually exist in the settings table
    print("--- 1. Inspecting Columns in ao_8ba09e_project_settings ---")
    cursor.execute("DESCRIBE ao_8ba09e_project_settings")
    for col in cursor.fetchall():
        print(f"Column: {col['Field']}")

    # 2. Search for the specific behavior names from your screenshots
    # Names: "Making RCCA Required field Read only...", "Make Build Numeric Field..."
    print("\n--- 2. Searching for specific behaviors from screenshots ---")
    names_to_find = [
        "%RCCA Required%",
        "%Build Numeric%",
        "%Hide Unhide Local Metadata%"
    ]
    
    # We'll search across every column in the table since we don't know the name of the "Name" column
    cursor.execute("DESCRIBE ao_8ba09e_project_settings")
    cols = [c['Field'] for c in cursor.fetchall()]
    
    for name_pattern in names_to_find:
        where_clause = " OR ".join([f"`{c}` LIKE %s" for c in cols])
        query = f"SELECT * FROM ao_8ba09e_project_settings WHERE {where_clause}"
        cursor.execute(query, tuple([name_pattern] * len(cols)))
        results = cursor.fetchall()
        for row in results:
            print(f"Match Found: {row}")

    conn.close()

if __name__ == "__main__":
    main()
