import mysql.connector
import configparser
import argparse
import json

def get_args():
    parser = argparse.ArgumentParser(description="Shared Behavior Mapping Diagnostic")
    parser.add_argument("--instance", required=True, help="Instance name from config.ini")
    return parser.parse_args()

def main():
    args = get_args()
    config = configparser.ConfigParser()
    config.read('config.ini')
    
    s = config[args.instance]
    conn = mysql.connector.connect(
        host=s['host'], user=s['user'], password=s['password'], 
        database=s['database'], port=s.getint('port', 3306)
    )
    cursor = conn.cursor(dictionary=True)

    # This query targets the confirmed ao_33a75d hash and joins the 
    # Detail table (Names) to the Mapping table (Projects).
    query = """
    SELECT 
        d.NAME as behavior_name,
        d.DESCRIPTION,
        m.PROJECT_KEY,
        m.PROJECT_ID
    FROM ao_33a75d_it_detail d
    LEFT JOIN ao_33a75d_it_m_workflows m ON d.ID = m.DETAIL_ID
    WHERE m.PROJECT_KEY = 'UAT1ESX' 
       OR m.PROJECT_ID = (SELECT id FROM project WHERE pkey = 'UAT1ESX')
       OR d.PROJECT_KEY = 'UAT1ESX'
    ORDER BY d.NAME;
    """

    print(f"--- Fetching Shared Behaviors for UAT1ESX from {args.instance} ---")
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        
        if not results:
            print("No behaviors found with a direct mapping to UAT1ESX in ao_33a75d.")
            print("Attempting Global Fetch...")
            # Fallback: Just show ALL behavior names to verify table content
            cursor.execute("SELECT NAME, PROJECT_KEY FROM ao_33a75d_it_detail LIMIT 10")
            print("\nSample Behaviors in Table:")
            for row in cursor.fetchall():
                print(f"- {row['NAME']} (Mapped Key: {row['PROJECT_KEY']})")
        else:
            print(f"Found {len(results)} mapped behaviors:\n")
            for row in results:
                print(f"Name: {row['behavior_name']}")
                print(f"Desc: {row['DESCRIPTION']}")
                print(f"Link: Project {row['PROJECT_KEY']} (ID: {row['PROJECT_ID']})")
                print("-" * 30)

    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
