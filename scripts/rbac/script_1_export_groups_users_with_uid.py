#!/usr/bin/env python3
"""
Export groups, users, permissions, and UIDs from RBAC and Alerts databases

This script connects to both rbacdb and alertsdb within the kfuse-configdb-0 pod
to extract comprehensive user and group information.

Prerequisites:
    - kubectl access to the cluster
    - kfuse-configdb-0 pod running
    - PostgreSQL credentials (default: password='password')

Output CSV format:
    group_name,user_email,user_id,permission,uid
    Engineering,john.doe@example.com,123,Admin,uid123
    Engineering,jane.smith@example.com,124,Member,uid124

Usage examples:
    # Basic usage (uses default password)
    python script_1_export_groups_users_with_uid.py
    
    # With custom password
    PGPASSWORD=mypassword python script_1_export_groups_users_with_uid.py
    
    # Use with script_3 for diff mode
    python script_1_export_groups_users_with_uid.py  # Export from RBAC DB
    python script_2_export_groups_users_grafana_api.py --user admin:password  # Export from Grafana
    python script_3_create_teams_and_add_users.py --user admin:password --diff grafana_teams_users_export.csv groups_users_export.csv
"""

import subprocess
import csv
import sys
import os

def execute_psql_query(query, database='rbacdb', password=None):
    """Execute a PostgreSQL query inside the kfuse-configdb-0 pod"""
    
    if password:
        # Use PGPASSWORD environment variable
        cmd = [
            'kubectl', 'exec', 'kfuse-configdb-0', '--',
            'env', f'PGPASSWORD={password}',
            'psql', '-U', 'postgres', '-d', database, '-t', '-A', '-c', query
        ]
    else:
        # Try without password (in case it's not required)
        cmd = [
            'kubectl', 'exec', 'kfuse-configdb-0', '--',
            'psql', '-U', 'postgres', '-d', database, '-t', '-A', '-c', query
        ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        if password is None and "password" in e.stderr.lower():
            # Password is required
            password = input("Enter PostgreSQL password for user 'postgres': ")
            return execute_psql_query(query, database, password)
        else:
            print(f"Error executing query on {database}: {e}")
            print(f"Error output: {e.stderr}")
            sys.exit(1)

def parse_psql_output(output):
    """Parse the pipe-separated output from psql"""
    if not output:
        return []
    
    rows = []
    for line in output.split('\n'):
        if line.strip():
            rows.append([field.strip() for field in line.split('|')])
    return rows

def main():
    # Get password from environment or use default
    password = os.environ.get('PGPASSWORD', 'password')
    
    # Query 1: Get groups and users from rbacdb with permissions
    query_rbac = """
    SELECT
        g.name AS group_name,
        u.email AS user_email,
        u.id AS user_id,
        gm.permission AS permission
    FROM groups g
    LEFT JOIN group_members gm ON g.id = gm.group_id
    LEFT JOIN users u ON u.id = gm.user_id
    ORDER BY g.name, u.email;
    """
    
    print("Executing query to fetch group and user data from rbacdb...")
    output_rbac = execute_psql_query(query_rbac, 'rbacdb', password)
    rbac_data = parse_psql_output(output_rbac)
    
    # Query 2: Get uid from alertsdb
    query_alerts = """
    SELECT email, uid
    FROM public.user
    WHERE email IS NOT NULL
    ORDER BY email;
    """
    
    print("Executing query to fetch uid from alertsdb...")
    output_alerts = execute_psql_query(query_alerts, 'alertsdb', password)
    alerts_data = parse_psql_output(output_alerts)
    
    # Create a dictionary for quick lookup of uid by email
    uid_lookup = {}
    for row in alerts_data:
        if len(row) >= 2:
            email = row[0]
            uid = row[1]
            uid_lookup[email] = uid
    
    # Merge the data
    merged_data = []
    for row in rbac_data:
        if len(row) >= 4:
            group_name = row[0]
            user_email = row[1]
            user_id = row[2]
            permission = row[3]
            
            # Look up the uid
            uid = uid_lookup.get(user_email, '') if user_email else ''
            
            merged_data.append([group_name, user_email, user_id, permission, uid])
    
    # Write to CSV file
    output_file = 'groups_users_export.csv'
    with open(output_file, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['group_name', 'user_email', 'user_id', 'permission', 'uid'])
        # Write data
        for row in merged_data:
            writer.writerow(row)
    
    print(f"\nData exported successfully to {output_file}")
    print(f"Total records exported: {len(merged_data)}")
    print(f"Records with uid found: {sum(1 for row in merged_data if row[4])}")
    
    # Show sample data
    if merged_data:
        print("\nSample data (first 5 rows):")
        print("-" * 100)
        print(f"{'Group Name':<20} {'User Email':<30} {'User ID':<10} {'Permission':<15} {'UID':<20}")
        print("-" * 100)
        for row in merged_data[:5]:
            print(f"{row[0] or 'N/A':<20} {row[1] or 'N/A':<30} {row[2] or 'N/A':<10} {row[3] or 'N/A':<15} {row[4] or 'N/A':<20}")

if __name__ == "__main__":
    main()