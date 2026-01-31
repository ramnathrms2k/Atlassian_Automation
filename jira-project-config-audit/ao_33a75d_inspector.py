import mysql.connector
import configparser
import argparse

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    s = config['SBX'] 
    conn = mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'], 
        database=s['database'], port=s.getint('port', 3306)
    )
    cursor = conn.cursor(dictionary=True)

    # We know the hash is ao_33a75d. Let's find all its tables and columns.
    print("--- Inspecting all tables in hash: ao_33a75d ---")
    query = """
    SELECT TABLE_NAME, COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME LIKE 'ao_33a75d%' 
    AND (COLUMN_NAME LIKE '%PROJECT%' OR COLUMN_NAME LIKE '%DETAIL%' OR COLUMN_NAME LIKE '%ID%')
    """
    cursor.execute(query)
    results = cursor.fetchall()
    
    tables = {}
    for row in results:
        t = row['TABLE_NAME']
        if t not in tables: tables[t] = []
        tables[t].append(row['COLUMN_NAME'])
    
    for table, cols in tables.items():
        print(f"Table: {table} | Columns: {', '.join(cols)}")

    conn.close()

if __name__ == "__main__":
    main()
