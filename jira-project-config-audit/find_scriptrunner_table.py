import mysql.connector
import configparser

def main():
    config = configparser.ConfigParser()
    config.read('config.ini')
    s = config['PRD'] 
    conn = mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'], 
        database=s['database'], port=s.getint('port', 3306)
    )
    cursor = conn.cursor(dictionary=True)

    # Search for the behavior name across EVERY table starting with AO_
    search_name = "Making RCCA Required field Read only for VCF UBM Projects"
    
    print(f"--- Scanning all AO tables for: '{search_name}' ---")
    
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'AO_%'")
    tables = [row['TABLE_NAME'] for row in cursor.fetchall()]
    
    for table in tables:
        try:
            cursor.execute(f"DESCRIBE {table}")
            cols = [col['Field'] for col in cursor.fetchall()]
            
            # Look for columns that might hold a name/string
            search_cols = [c for c in cols if 'NAME' in c.upper() or 'DESC' in c.upper() or 'FIELD' in c.upper()]
            if not search_cols: continue
            
            where_clause = " OR ".join([f"`{c}` = %s" for c in search_cols])
            query = f"SELECT * FROM {table} WHERE {where_clause}"
            cursor.execute(query, tuple([search_name] * len(search_cols)))
            
            res = cursor.fetchall()
            if res:
                print(f"\n[!] MATCH FOUND in Table: {table}")
                print(f"Columns in this table: {', '.join(cols)}")
                print(f"Row Data: {res[0]}")
                
        except:
            continue

    conn.close()

if __name__ == "__main__":
    main()
