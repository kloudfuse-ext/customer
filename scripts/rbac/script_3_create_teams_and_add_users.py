#!/usr/bin/env python3
"""
Create teams and add users to teams in Grafana from CSV file

Prerequisites:
    python3 -m venv venv
    source venv/bin/activate
    pip install requests

Input CSV format (simple):
    group_name,user_email
    Engineering,john.doe@example.com
    Engineering,jane.smith@example.com
    Marketing,bob.jones@example.com

Input CSV format (with permissions):
    group_name,user_email,user_id,permission,uid
    Engineering,john.doe@example.com,123,Admin,uid123
    Engineering,jane.smith@example.com,124,Member,uid124

Usage examples:
    # Basic authentication with CSV file
    python script_3_create_teams_and_add_users.py --user admin:password --input teams_users.csv
    
    # API key authentication
    python script_3_create_teams_and_add_users.py --api-key YOUR_API_KEY --input teams_users.csv
    
    # With custom URL
    python script_3_create_teams_and_add_users.py --user admin:password --input teams_users.csv --url https://your-grafana.com/grafana
    
    # Dry run mode (preview changes without applying)
    python script_3_create_teams_and_add_users.py --user admin:password --input teams_users.csv --dry-run
    
    # Diff mode - only process differences between two CSV files
    python script_3_create_teams_and_add_users.py --user admin:password --diff grafana_export.csv rbac_export.csv
    
    # Diff mode with dry run
    python script_3_create_teams_and_add_users.py --user admin:password --diff grafana_export.csv rbac_export.csv --dry-run
"""

import requests
import csv
import sys
import os
import argparse
import urllib3
from requests.auth import HTTPBasicAuth
from collections import defaultdict

# Disable SSL warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_all_teams(base_url, headers, auth=None, verify_ssl=True):
    """Fetch all teams from Grafana"""
    url = f"{base_url}/api/teams/search?perpage=1000"
    try:
        response = requests.get(url, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching teams: {e}")
        return None

def get_all_users(base_url, headers, auth=None, verify_ssl=True):
    """Fetch all users from Grafana"""
    url = f"{base_url}/api/users?perpage=1000"
    try:
        response = requests.get(url, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching users: {e}")
        return None

def create_team(base_url, team_name, headers, auth=None, verify_ssl=True):
    """Create a new team in Grafana"""
    url = f"{base_url}/api/teams"
    data = {"name": team_name}
    
    try:
        response = requests.post(url, json=data, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 409:
            print(f"  Team '{team_name}' already exists")
            return None
        print(f"  Error creating team '{team_name}': {e}")
        return None

def add_user_to_team(base_url, team_id, user_id, permission='Member', headers=None, auth=None, verify_ssl=True):
    """Add a user to a team with specified permission"""
    url = f"{base_url}/api/teams/{team_id}/members"
    data = {"userId": user_id}
    
    # Note: Grafana's team API doesn't support setting permissions directly when adding members
    # Permissions are managed separately through RBAC or team roles
    
    try:
        response = requests.post(url, json=data, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 400:
            # User might already be in the team
            error_msg = e.response.json().get('message', '')
            if 'already added' in error_msg.lower():
                return True
        print(f"    Error adding user to team: {e}")
        return False

def read_csv_file(filename):
    """Read CSV file and return grouped data with permissions"""
    teams_users = defaultdict(list)
    
    try:
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                group_name = row.get('group_name', '').strip()
                user_email = row.get('user_email', '').strip()
                permission = row.get('permission', 'Member').strip()  # Default to Member if not specified
                
                if group_name and user_email:
                    teams_users[group_name].append({
                        'email': user_email,
                        'permission': permission
                    })
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    return teams_users

def compute_diff(file1, file2):
    """Compute differences between two CSV files"""
    print(f"\nComputing differences between:")
    print(f"  File 1 (existing): {file1}")
    print(f"  File 2 (desired): {file2}")
    
    # Read both files
    existing_data = defaultdict(set)
    desired_data = defaultdict(set)
    
    # Read existing state (file1)
    try:
        with open(file1, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                group_name = row.get('group_name', '').strip()
                user_email = row.get('user_email', '').strip()
                permission = row.get('permission', 'Member').strip()
                
                if group_name and user_email:
                    existing_data[group_name].add((user_email, permission))
    except Exception as e:
        print(f"Error reading file1 ({file1}): {e}")
        sys.exit(1)
    
    # Read desired state (file2)
    try:
        with open(file2, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                group_name = row.get('group_name', '').strip()
                user_email = row.get('user_email', '').strip()
                permission = row.get('permission', 'Member').strip()
                
                if group_name and user_email:
                    desired_data[group_name].add((user_email, permission))
    except Exception as e:
        print(f"Error reading file2 ({file2}): {e}")
        sys.exit(1)
    
    # Compute differences
    diff_data = defaultdict(list)
    
    # Find new teams and new members
    all_teams = set(desired_data.keys()) | set(existing_data.keys())
    
    for team in all_teams:
        existing_members = existing_data.get(team, set())
        desired_members = desired_data.get(team, set())
        
        # Find members to add (in desired but not in existing)
        members_to_add = desired_members - existing_members
        
        for email, permission in members_to_add:
            diff_data[team].append({
                'email': email,
                'permission': permission,
                'action': 'add'
            })
    
    # Summary
    print(f"\nDiff Summary:")
    new_teams = set(desired_data.keys()) - set(existing_data.keys())
    print(f"  New teams to create: {len(new_teams)}")
    if new_teams:
        for team in sorted(new_teams):
            print(f"    - {team}")
    
    total_additions = sum(len([m for m in members if m['action'] == 'add']) for members in diff_data.values())
    print(f"  Total user additions: {total_additions}")
    
    # Convert diff_data to the format expected by the rest of the script
    result = defaultdict(list)
    for team, members in diff_data.items():
        for member in members:
            if member['action'] == 'add':
                result[team].append({
                    'email': member['email'],
                    'permission': member['permission']
                })
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Create teams and add users in Grafana from CSV')
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input', '-i',
                            help='Input CSV file with group_name and user_email columns')
    input_group.add_argument('--diff', nargs=2, metavar=('EXISTING_CSV', 'DESIRED_CSV'),
                            help='Compute diff between two CSV files and apply changes')
    
    # Authentication options
    auth_group = parser.add_mutually_exclusive_group(required=True)
    auth_group.add_argument('--user', '-u', 
                           help='Basic auth in format username:password (e.g., admin:password)')
    auth_group.add_argument('--api-key', '-k', 
                           help='Grafana API key')
    auth_group.add_argument('--service-account-token', '-s', 
                           help='Grafana service account token')
    
    # Other options
    parser.add_argument('--url', 
                       default=os.environ.get('GRAFANA_URL', 'https://sk-dev.kloudfuse.io/grafana'),
                       help='Grafana URL (default: https://sk-dev.kloudfuse.io/grafana or GRAFANA_URL env var)')
    parser.add_argument('--no-verify-ssl', 
                       action='store_true',
                       help='Disable SSL certificate verification')
    parser.add_argument('--dry-run',
                       action='store_true',
                       help='Preview changes without applying them')
    parser.add_argument('--org-id',
                       help='Grafana organization ID (for multi-org setups)')
    
    args = parser.parse_args()
    
    # Set up authentication
    headers = {'Content-Type': 'application/json'}
    auth = None
    
    if args.user:
        if ':' not in args.user:
            print("Error: --user must be in format username:password")
            sys.exit(1)
        username, password = args.user.split(':', 1)
        auth = HTTPBasicAuth(username, password)
        print(f"Using basic authentication with user: {username}")
    elif args.api_key:
        headers['Authorization'] = f'Bearer {args.api_key}'
        print("Using API key authentication")
    elif args.service_account_token:
        headers['Authorization'] = f'Bearer {args.service_account_token}'
        print("Using service account token authentication")
    
    if args.org_id:
        headers['X-Grafana-Org-Id'] = args.org_id
    
    grafana_url = args.url.rstrip('/')
    verify_ssl = not args.no_verify_ssl
    
    # Read or compute data
    if args.diff:
        # Diff mode
        teams_users = compute_diff(args.diff[0], args.diff[1])
        if not teams_users:
            print("\nNo differences found. Grafana is already in sync.")
            sys.exit(0)
    else:
        # Normal mode - read single CSV file
        print(f"\nReading CSV file: {args.input}")
        teams_users = read_csv_file(args.input)
    
    print(f"Found {len(teams_users)} teams with {sum(len(users) for users in teams_users.values())} user assignments")
    
    if args.dry_run:
        print("\n=== DRY RUN MODE - No changes will be made ===")
    
    # Fetch existing teams and users
    print(f"\nConnecting to Grafana at: {grafana_url}")
    print("Fetching existing teams...")
    teams_response = get_all_teams(grafana_url, headers, auth, verify_ssl)
    if not teams_response:
        print("Failed to fetch teams")
        sys.exit(1)
    
    existing_teams = {team['name']: team for team in teams_response.get('teams', [])}
    print(f"Found {len(existing_teams)} existing teams")
    
    print("\nFetching existing users...")
    users_response = get_all_users(grafana_url, headers, auth, verify_ssl)
    if not users_response:
        print("Failed to fetch users")
        sys.exit(1)
    
    existing_users = {user['email']: user for user in users_response if user.get('email')}
    print(f"Found {len(existing_users)} existing users")
    
    # Process teams and users
    print("\n" + "="*60)
    stats = {
        'teams_created': 0,
        'teams_existed': 0,
        'users_added': 0,
        'users_not_found': 0,
        'users_already_in_team': 0
    }
    
    for team_name, users in teams_users.items():
        print(f"\nProcessing team: {team_name}")
        
        # Create team if it doesn't exist
        if team_name in existing_teams:
            print(f"  Team already exists (ID: {existing_teams[team_name]['id']})")
            team_id = existing_teams[team_name]['id']
            stats['teams_existed'] += 1
        else:
            if args.dry_run:
                print(f"  [DRY RUN] Would create team: {team_name}")
                stats['teams_created'] += 1
                continue
            else:
                print(f"  Creating team: {team_name}")
                result = create_team(grafana_url, team_name, headers, auth, verify_ssl)
                if result:
                    team_id = result['teamId']
                    existing_teams[team_name] = {'id': team_id, 'name': team_name}
                    stats['teams_created'] += 1
                else:
                    continue
        
        # Add users to team
        print(f"  Adding {len(users)} users to team...")
        for user_info in users:
            email = user_info['email'] if isinstance(user_info, dict) else user_info
            permission = user_info.get('permission', 'Member') if isinstance(user_info, dict) else 'Member'
            
            if email not in existing_users:
                print(f"    ❌ User not found: {email}")
                stats['users_not_found'] += 1
                continue
            
            user = existing_users[email]
            user_id = user['id']
            
            if args.dry_run:
                print(f"    [DRY RUN] Would add user: {email} (ID: {user_id}) with permission: {permission}")
                stats['users_added'] += 1
            else:
                print(f"    Adding user: {email} (ID: {user_id}) with permission: {permission}")
                if add_user_to_team(grafana_url, team_id, user_id, permission, headers, auth, verify_ssl):
                    stats['users_added'] += 1
                else:
                    stats['users_already_in_team'] += 1
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  Teams created: {stats['teams_created']}")
    print(f"  Teams already existed: {stats['teams_existed']}")
    print(f"  Users added to teams: {stats['users_added']}")
    print(f"  Users not found in Grafana: {stats['users_not_found']}")
    if stats['users_already_in_team'] > 0:
        print(f"  Users already in teams: {stats['users_already_in_team']}")
    
    if args.dry_run:
        print("\n=== DRY RUN COMPLETE - No changes were made ===")
    else:
        print("\n✅ Operation completed successfully!")

if __name__ == "__main__":
    main()