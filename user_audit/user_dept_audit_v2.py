import mysql.connector
import configparser
import csv
import argparse
import datetime
import sys
import os

def get_config():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config

def get_db_connection(config_section):
    return mysql.connector.connect(
        host=config_section['host'],
        user=config_section['user'],
        password=config_section['password'],
        database=config_section['database']
    )

def format_jira_date(ms_timestamp):
    if not ms_timestamp: return None
    try:
        return datetime.datetime.fromtimestamp(int(ms_timestamp) / 1000.0).date()
    except:
        return None

def main():
    parser = argparse.ArgumentParser(description='Export Active Licensed Users with HR Dept and Last Login.')
    parser.add_argument('app', choices=['jira', 'confluence'], help='Target application (jira or confluence)')
    args = parser.parse_args()

    config = get_config()
    app_conn = None
    hr_conn = None
    
    threshold_days = 90
    inactivity_limit = datetime.date.today() - datetime.timedelta(days=threshold_days)

    try:
        app_section = 'JIRA_DB' if args.app == 'jira' else 'CONFLUENCE_DB'
        print(f"[*] Connecting to {args.app.upper()} database...")
        app_conn = get_db_connection(config[app_section])
        app_cursor = app_conn.cursor(dictionary=True)

        if args.app == 'jira':
            group_name = 'jira-users'
            query = """
            SELECT DISTINCT u.lower_user_name as userid, u.email_address, u.display_name, ua.attribute_value as last_login
            FROM cwd_user u
            JOIN cwd_membership m ON u.id = m.child_id
            JOIN cwd_group g ON m.parent_id = g.id
            LEFT JOIN cwd_user_attributes ua ON u.id = ua.user_id AND ua.attribute_name = 'login.lastLoginMillis'
            WHERE u.active = 1 AND g.group_name = %s
            """
        else:
            group_name = 'confluence-users'
            # Modern Confluence 9.x Join: u -> user_mapping -> logininfo
            print(f"[*] Using Confluence Join: user_mapping link for SUCCESSDATE")
            query = """
            SELECT DISTINCT u.lower_user_name as userid, u.email_address, u.display_name, li.SUCCESSDATE as last_login
            FROM cwd_user u
            JOIN cwd_membership m ON u.id = m.child_user_id
            JOIN cwd_group g ON m.parent_id = g.id
            JOIN user_mapping um ON u.lower_user_name = um.lower_username
            LEFT JOIN logininfo li ON um.user_key = li.USERNAME
            WHERE (u.active = 'T' OR u.active = '1' OR u.active = 'active')
              AND g.group_name = %s
            """

        app_cursor.execute(query, (group_name,))
        users = app_cursor.fetchall()
        
        if not users:
            print(f"[!] No active users found in {args.app.upper()} for group {group_name}.")
            return

        print(f"[+] Found {len(users)} active licensed users.")
        print("[*] Connecting to HR database...")
        hr_conn = get_db_connection(config['HR_DB'])
        hr_cursor = hr_conn.cursor()

        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"{args.app}_user_audit_{timestamp}.csv"
        
        not_found_in_hr = 0
        reclaimable_licenses = 0

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['User ID', 'Email Address', 'Display Name', 'Department', 'Last Login Date'])

            for user in users:
                hr_cursor.execute("SELECT division FROM tb_hr_employees_all WHERE userid = %s AND source = 'corp' LIMIT 1", (user['userid'],))
                result = hr_cursor.fetchone()
                dept = result[0] if result else "NOT FOUND"
                if dept == "NOT FOUND": not_found_in_hr += 1

                raw_login = user['last_login']
                login_date_obj = None
                
                if args.app == 'jira':
                    login_date_obj = format_jira_date(raw_login)
                elif raw_login:
                    if isinstance(raw_login, (datetime.datetime, datetime.date)):
                        login_date_obj = raw_login.date() if isinstance(raw_login, datetime.datetime) else raw_login

                is_inactive = (login_date_obj is None) or (login_date_obj < inactivity_limit)
                if dept == "NOT FOUND" and is_inactive:
                    reclaimable_licenses += 1

                display_date = login_date_obj.strftime('%Y-%m-%d') if login_date_obj else "Never"
                writer.writerow([user['userid'], user['email_address'], user['display_name'], dept, display_date])

        print("-" * 50)
        print(f"AUDIT SUMMARY FOR {args.app.upper()}")
        print("-" * 50)
        print(f"Total Licensed Users:      {len(users)}")
        print(f"Users NOT in HR DB:        {not_found_in_hr}")
        print(f"Potential Ghost Licenses:   {reclaimable_licenses}")
        print("-" * 50)
        print(f"[SUCCESS] File saved: {output_file}")

    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        if app_conn and app_conn.is_connected(): app_conn.close()
        if hr_conn and hr_conn.is_connected(): hr_conn.close()

if __name__ == "__main__":
    main()
