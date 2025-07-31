#!/usr/bin/env python3
"""
Export Grafana teams and users to CSV using Grafana API

Prerequisites:
    python3 -m venv venv
    source venv/bin/activate
    pip install requests

Usage examples:
    # Basic authentication
    python script_2_export_groups_users_grafana_api.py --user admin:password
    
    # API key authentication
    python script_2_export_groups_users_grafana_api.py --api-key YOUR_API_KEY
    
    # Service account token
    python script_2_export_groups_users_grafana_api.py --service-account-token YOUR_TOKEN
    
    # With custom URL
    python script_2_export_groups_users_grafana_api.py --user admin:password --url https://your-grafana.com/grafana
    
    # With multiple custom options
    python script_2_export_groups_users_grafana_api.py --user admin:password --no-verify-ssl --output my_export.csv --url https://grafana.example.com
"""

import requests
import csv
import sys
import os
import argparse
import urllib3
from requests.auth import HTTPBasicAuth

# Disable SSL warnings if needed
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_grafana_teams(base_url, headers, auth=None, verify_ssl=True):
    """Fetch all teams from Grafana"""
    url = f"{base_url}/api/teams/search"
    try:
        response = requests.get(url, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching teams: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
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

def get_user_details(base_url, user_id, headers, auth=None, verify_ssl=True):
    """Fetch user details by user ID"""
    url = f"{base_url}/api/users/{user_id}"
    try:
        response = requests.get(url, headers=headers, auth=auth, verify=verify_ssl)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching user {user_id} details: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Export Grafana teams and users to CSV')
    
    # Authentication options
    auth_group = parser.add_mutually_exclusive_group()
    auth_group.add_argument('--user', '-u', 
                           help='Basic auth in format username:password (e.g., admin:password)')
    auth_group.add_argument('--api-key', '-k', 
                           help='Grafana API key')
    auth_group.add_argument('--service-account-token', '-s', 
                           help='Grafana service account token')
    
    # Other options
    parser.add_argument('--url', 
                       default=os.environ.get('GRAFANA_URL', 'https://pisco.kloudfuse.io/grafana'),
                       help='Grafana URL (default: https://sk-dev.kloudfuse.io/grafana or GRAFANA_URL env var)')
    parser.add_argument('--no-verify-ssl', 
                       action='store_true',
                       help='Disable SSL certificate verification')
    parser.add_argument('--output', '-o',
                       default='grafana_teams_users_export.csv',
                       help='Output CSV filename (default: grafana_teams_users_export.csv)')
    parser.add_argument('--org-id',
                       help='Grafana organization ID (for multi-org setups)')
    parser.add_argument('--debug',
                       action='store_true',
                       help='Enable debug output')
    
    args = parser.parse_args()
    
    # Determine authentication method
    headers = {'Content-Type': 'application/json'}
    auth = None
    
    if args.user:
        # Basic authentication
        if ':' not in args.user:
            print("Error: --user must be in format username:password")
            sys.exit(1)
        username, password = args.user.split(':', 1)
        auth = HTTPBasicAuth(username, password)
        print(f"Using basic authentication with user: {username}")
    elif args.api_key:
        # API key authentication
        headers['Authorization'] = f'Bearer {args.api_key}'
        print("Using API key authentication")
    elif args.service_account_token:
        # Service account token authentication
        headers['Authorization'] = f'Bearer {args.service_account_token}'
        print("Using service account token authentication")
    elif os.environ.get('GRAFANA_API_KEY'):
        # Try environment variable
        headers['Authorization'] = f'Bearer {os.environ.get("GRAFANA_API_KEY")}'
        print("Using API key from GRAFANA_API_KEY environment variable")
    else:
        print("Error: No authentication method provided")
        print("Use one of the following:")
        print("  --user admin:password         (Basic authentication)")
        print("  --api-key YOUR_API_KEY       (API key authentication)")
        print("  --service-account-token TOKEN (Service account token)")
        print("  GRAFANA_API_KEY=xxx python3 script_2_export_groups_users_grafana_api.py")
        sys.exit(1)
    
    # Add organization header if specified
    if args.org_id:
        headers['X-Grafana-Org-Id'] = args.org_id
    
    grafana_url = args.url.rstrip('/')
    verify_ssl = not args.no_verify_ssl
    
    print(f"Connecting to Grafana at: {grafana_url}")
    print(f"SSL verification: {verify_ssl}")
    
    if args.debug:
        print(f"Headers: {headers}")
    
    # Fetch all teams
    print("\nFetching teams from Grafana...")
    teams_response = get_grafana_teams(grafana_url, headers, auth, verify_ssl)
    
    if not teams_response:
        print("Failed to fetch teams")
        sys.exit(1)
    
    teams = teams_response.get('teams', [])
    print(f"Found {len(teams)} teams")
    
    # Collect all data
    all_data = []
    
    for team in teams:
        team_id = team.get('id')
        team_name = team.get('name', 'Unknown Team')
        
        print(f"\nProcessing team: {team_name} (ID: {team_id})")
        
        # Get team members
        members = get_team_members(grafana_url, team_id, headers, auth, verify_ssl)
        
        if not members:
            # Add empty row for teams with no members
            all_data.append([team_name, '', '', ''])
            continue
        
        for member in members:
            user_id = member.get('userId')
            user_email = member.get('email', '')
            
            # If email is not in the member response, fetch user details
            if not user_email and user_id:
                user_details = get_user_details(grafana_url, user_id, headers, auth, verify_ssl)
                if user_details:
                    user_email = user_details.get('email', '')
                    user_login = user_details.get('login', '')
                else:
                    user_login = member.get('login', '')
            else:
                user_login = member.get('login', '')
            
            # Add to data collection
            all_data.append([
                team_name,
                user_email,
                str(user_id) if user_id else '',
                user_login
            ])
    
    # Write to CSV file
    with open(args.output, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        # Write header
        writer.writerow(['group_name', 'user_email', 'user_id', 'user_login'])
        # Write data
        for row in all_data:
            writer.writerow(row)
    
    print(f"\nData exported successfully to {args.output}")
    print(f"Total records exported: {len(all_data)}")
    
    # Show sample data
    if all_data:
        print("\nSample data (first 5 rows):")
        print("-" * 100)
        print(f"{'Group Name':<25} {'User Email':<30} {'User ID':<15} {'User Login':<20}")
        print("-" * 100)
        for row in all_data[:5]:
            print(f"{row[0]:<25} {row[1]:<30} {row[2]:<15} {row[3]:<20}")

if __name__ == "__main__":
    main()