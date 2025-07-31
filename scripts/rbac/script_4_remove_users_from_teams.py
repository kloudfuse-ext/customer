#!/usr/bin/env python3
"""
Remove users from teams in Grafana based on CSV file or diff between two CSV files

Prerequisites:
    python3 -m venv venv
    source venv/bin/activate
    pip install requests

Input CSV format:
    group_name,user_email
    Engineering,john.doe@example.com
    Engineering,jane.smith@example.com
    Marketing,bob.jones@example.com

Usage examples:
    # Remove users from teams based on CSV file
    python script_4_remove_users_from_teams.py --user admin:password --input users_to_remove.csv
    
    # API key authentication
    python script_4_remove_users_from_teams.py --api-key YOUR_API_KEY --input users_to_remove.csv
    
    # With custom URL
    python script_4_remove_users_from_teams.py --user admin:password --input users_to_remove.csv --url https://your-grafana.com/grafana
    
    # Dry run mode (preview changes without applying)
    python script_4_remove_users_from_teams.py --user admin:password --input users_to_remove.csv --dry-run
    
    # Diff mode - remove users that exist in first file but not in second file
    python script_4_remove_users_from_teams.py --user admin:password --diff current_state.csv desired_state.csv
    
    # Diff mode with dry run
    python script_4_remove_users_from_teams.py --user admin:password --diff current_state.csv desired_state.csv --dry-run
    
    # Complete workflow example:
    # 1. Export current Grafana state
    python script_2_export_groups_users_grafana_api.py --user admin:password
    # 2. Export desired RBAC state  
    python script_1_export_groups_users_with_uid.py
    # 3. Remove users that are in Grafana but not in RBAC
    python script_4_remove_users_from_teams.py --user admin:password --diff grafana_teams_users_export.csv groups_users_export.csv
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

def get_team_members(base_url, team_id, headers, auth=None, verify_ssl=True):
    """Fetch members of a specific team"""
    url = f"{base_url}/api/teams/{team_id}/members"
    try:
        response = requests.get(url, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching team {team_id} members: {e}")
        return []

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

def remove_user_from_team(base_url, team_id, user_id, headers, auth=None, verify_ssl=True):
    """Remove a user from a team"""
    url = f"{base_url}/api/teams/{team_id}/members/{user_id}"
    
    try:
        response = requests.delete(url, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
            # User is not in the team
            print(f"    User not found in team (already removed)")
            return True
        print(f"    Error removing user from team: {e}")
        return False

def read_csv_file(filename):
    """Read CSV file and return grouped data"""
    teams_users = defaultdict(list)
    
    try:
        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                group_name = row.get('group_name', '').strip()
                user_email = row.get('user_email', '').strip()
                
                if group_name and user_email:
                    teams_users[group_name].append(user_email)
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        sys.exit(1)
    
    return teams_users

def compute_removal_diff(current_file, desired_file):
    """Compute which users should be removed (in current but not in desired)"""
    print(f"\nComputing users to remove:")
    print(f"  Current state: {current_file}")
    print(f"  Desired state: {desired_file}")
    
    # Read both files
    current_data = defaultdict(set)
    desired_data = defaultdict(set)
    
    # Read current state
    try:
        with open(current_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                group_name = row.get('group_name', '').strip()
                user_email = row.get('user_email', '').strip()
                
                if group_name and user_email:
                    current_data[group_name].add(user_email)
    except Exception as e:
        print(f"Error reading current file ({current_file}): {e}")
        sys.exit(1)
    
    # Read desired state
    try:
        with open(desired_file, 'r') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                group_name = row.get('group_name', '').strip()
                user_email = row.get('user_email', '').strip()
                
                if group_name and user_email:
                    desired_data[group_name].add(user_email)
    except Exception as e:
        print(f"Error reading desired file ({desired_file}): {e}")
        sys.exit(1)
    
    # Compute users to remove (in current but not in desired)
    removal_data = defaultdict(list)
    
    for team in current_data:
        current_members = current_data[team]
        desired_members = desired_data.get(team, set())
        
        # Find members to remove (in current but not in desired)
        members_to_remove = current_members - desired_members
        
        for email in members_to_remove:
            removal_data[team].append(email)
    
    # Summary
    print(f"\nRemoval Summary:")
    total_removals = sum(len(users) for users in removal_data.values())
    print(f"  Total user removals: {total_removals}")
    
    if total_removals > 0:
        print(f"  Teams with removals: {len(removal_data)}")
        for team, users in removal_data.items():
            print(f"    {team}: {len(users)} user(s) to remove")
    
    return removal_data

def main():
    parser = argparse.ArgumentParser(description='Remove users from teams in Grafana')
    
    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('--input', '-i',
                            help='Input CSV file with group_name and user_email columns for users to remove')
    input_group.add_argument('--diff', nargs=2, metavar=('CURRENT_CSV', 'DESIRED_CSV'),
                            help='Remove users that exist in CURRENT_CSV but not in DESIRED_CSV')
    
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
        # Diff mode - find users to remove
        teams_users = compute_removal_diff(args.diff[0], args.diff[1])
        if not teams_users:
            print("\nNo users need to be removed. System is already in sync.")
            sys.exit(0)
    else:
        # Normal mode - read single CSV file
        print(f"\nReading CSV file: {args.input}")
        teams_users = read_csv_file(args.input)
    
    print(f"Found {len(teams_users)} teams with {sum(len(users) for users in teams_users.values())} user removals to process")
    
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
    
    # Process removals
    print("\n" + "="*60)
    stats = {
        'teams_not_found': 0,
        'users_removed': 0,
        'users_not_found': 0,
        'users_not_in_team': 0,
        'admin_skipped': 0
    }
    
    for team_name, user_emails in teams_users.items():
        print(f"\nProcessing team: {team_name}")
        
        # Check if team exists
        if team_name not in existing_teams:
            print(f"  [X] Team '{team_name}' not found in Grafana")
            stats['teams_not_found'] += 1
            continue
        
        team_id = existing_teams[team_name]['id']
        print(f"  Team found (ID: {team_id})")
        
        # Remove users from team
        print(f"  Removing {len(user_emails)} users from team...")
        for email in user_emails:
            # Skip admin user
            if email.lower() in ['admin@localhost', 'admin']:
                print(f"    [SKIP] Skipping admin user: {email}")
                stats['admin_skipped'] += 1
                continue
                
            if email not in existing_users:
                print(f"    [X] User not found: {email}")
                stats['users_not_found'] += 1
                continue
            
            user = existing_users[email]
            user_id = user['id']
            
            # Double-check for admin by login name
            if user.get('login', '').lower() == 'admin':
                print(f"    [SKIP] Skipping admin user: {email} (login: {user.get('login')})")
                stats['admin_skipped'] += 1
                continue
            
            if args.dry_run:
                print(f"    [DRY RUN] Would remove user: {email} (ID: {user_id})")
                stats['users_removed'] += 1
            else:
                print(f"    Removing user: {email} (ID: {user_id})")
                if remove_user_from_team(grafana_url, team_id, user_id, headers, auth, verify_ssl):
                    stats['users_removed'] += 1
                else:
                    stats['users_not_in_team'] += 1
    
    # Print summary
    print("\n" + "="*60)
    print("SUMMARY:")
    print(f"  Teams not found: {stats['teams_not_found']}")
    print(f"  Users removed from teams: {stats['users_removed']}")
    print(f"  Users not found in Grafana: {stats['users_not_found']}")
    if stats['admin_skipped'] > 0:
        print(f"  Admin users skipped: {stats['admin_skipped']}")
    if stats['users_not_in_team'] > 0:
        print(f"  Users not in teams (already removed): {stats['users_not_in_team']}")
    
    if args.dry_run:
        print("\n=== DRY RUN COMPLETE - No changes were made ===")
    else:
        print("\n[SUCCESS] Operation completed successfully!")

if __name__ == "__main__":
    main()