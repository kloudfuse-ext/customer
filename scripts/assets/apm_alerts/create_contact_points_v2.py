#!/usr/bin/env python3
"""
Script to create contact points in Grafana using the new provisioning API.
This version uses the /api/v1/provisioning/contact-points endpoint.
"""

import argparse
import csv
import json
import requests
from requests.auth import HTTPBasicAuth
from typing import List, Dict, Any


class GrafanaProvisioningClient:
    """Client for interacting with Grafana provisioning API."""

    def __init__(self, grafana_server: str, username: str = "admin", password: str = "password"):
        """Initialize the Grafana client."""
        self.server = grafana_server.rstrip('/')
        if not self.server.startswith(('http://', 'https://')):
            self.server = f"https://{self.server}"

        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(self.username, self.password)
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def get_contact_points(self) -> List[Dict[str, Any]]:
        """Get all contact points from Grafana."""
        url = f"{self.server}/api/v1/provisioning/contact-points"
        response = requests.get(url, auth=self.auth, headers=self.headers, timeout=30)

        if response.status_code != 200:
            print(f"Failed to get contact points: {response.status_code} - {response.text}")
            return []

        return response.json()

    def create_contact_point(self, contact_point: Dict[str, Any]) -> bool:
        """Create a new contact point in Grafana."""
        url = f"{self.server}/api/v1/provisioning/contact-points"
        response = requests.post(
            url,
            auth=self.auth,
            headers=self.headers,
            data=json.dumps(contact_point),
            timeout=30
        )

        if response.status_code in [200, 201, 202]:
            print(f"Successfully created contact point: {contact_point['name']}")
            return True
        else:
            print(f"Failed to create contact point {contact_point['name']}: {response.status_code} - {response.text}")
            return False

    def update_contact_point(self, uid: str, contact_point: Dict[str, Any]) -> bool:
        """Update an existing contact point in Grafana."""
        url = f"{self.server}/api/v1/provisioning/contact-points/{uid}"
        response = requests.put(
            url,
            auth=self.auth,
            headers=self.headers,
            data=json.dumps(contact_point),
            timeout=30
        )

        if response.status_code in [200, 202]:
            print(f"Successfully updated contact point: {contact_point['name']}")
            return True
        else:
            print(f"Failed to update contact point {contact_point['name']}: {response.status_code} - {response.text}")
            return False

    def delete_contact_point(self, uid: str) -> bool:
        """Delete a contact point from Grafana."""
        url = f"{self.server}/api/v1/provisioning/contact-points/{uid}"
        response = requests.delete(url, auth=self.auth, headers=self.headers, timeout=30)

        if response.status_code in [200, 202, 204]:
            return True
        else:
            print(f"Failed to delete contact point {uid}: {response.status_code} - {response.text}")
            return False


def parse_csv_contact_points(csv_file: str) -> List[Dict[str, Any]]:
    """Parse contact points from CSV file."""
    contact_points = []

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows
            if not row.get('Name'):
                continue

            # Build contact point based on type
            contact_type = row.get('Type', 'email').lower()
            name = f"{row['Name']}_kfuse_managed"

            contact_point = {
                "uid": "",  # Let Grafana generate the UID
                "name": name,
                "type": contact_type,
                "disableResolveMessage": False
            }

            if contact_type == 'email':
                contact_point["settings"] = {
                    "addresses": row.get('Email', ''),
                    "singleEmail": False
                }
                # Add message and subject if provided
                if row.get('Message'):
                    contact_point["settings"]["message"] = row['Message']
                if row.get('Subject'):
                    contact_point["settings"]["subject"] = row['Subject']

            elif contact_type == 'slack':
                contact_point["settings"] = {
                    "url": row.get('WebhookURL', ''),
                    "username": row.get('Username', 'Grafana'),
                }
                # Add optional fields if provided
                if row.get('Channel'):
                    contact_point["settings"]["recipient"] = row['Channel']
                if row.get('Title'):
                    contact_point["settings"]["title"] = row['Title']
                if row.get('Text'):
                    contact_point["settings"]["text"] = row['Text']

            elif contact_type == 'webhook':
                contact_point["settings"] = {
                    "url": row.get('WebhookURL', ''),
                    "httpMethod": row.get('Method', 'POST'),
                }
                # Add optional auth if provided
                if row.get('Username') and row.get('Password'):
                    contact_point["settings"]["username"] = row['Username']
                    contact_point["settings"]["password"] = row['Password']

            contact_points.append(contact_point)

    return contact_points


def sync_contact_points(client: GrafanaProvisioningClient, contact_points: List[Dict[str, Any]], replace_all: bool = False):
    """Sync contact points with Grafana."""
    # Get existing contact points
    existing = client.get_contact_points()
    existing_by_name = {cp['name']: cp for cp in existing}

    # Track managed contact points
    managed_suffix = "_kfuse_managed"

    if replace_all:
        # Delete all managed contact points first
        for name, cp in existing_by_name.items():
            if name.endswith(managed_suffix):
                print(f"Deleting managed contact point: {name}")
                client.delete_contact_point(cp['uid'])

    # Create or update contact points
    for cp in contact_points:
        name = cp['name']
        if name in existing_by_name:
            # Update existing
            existing_cp = existing_by_name[name]
            cp['uid'] = existing_cp['uid']  # Preserve UID for update
            print(f"Updating contact point: {name}")
            client.update_contact_point(existing_cp['uid'], cp)
        else:
            # Create new
            print(f"Creating contact point: {name}")
            client.create_contact_point(cp)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Create contact points in Grafana using provisioning API")
    parser.add_argument(
        "-g", "--grafana-server",
        required=True,
        help="Grafana server address (e.g., https://grafana.example.com/grafana)"
    )
    parser.add_argument(
        "-u", "--username",
        default="admin",
        help="Grafana username (default: admin)"
    )
    parser.add_argument(
        "-p", "--password",
        default="password",
        help="Grafana password (default: password)"
    )
    parser.add_argument(
        "-c", "--csv-file",
        required=True,
        help="CSV file containing contact points configuration"
    )
    parser.add_argument(
        "--replace-all",
        action="store_true",
        help="Replace all managed contact points (delete existing managed ones first)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print contact points that would be created without actually creating them"
    )

    args = parser.parse_args()

    # Parse contact points from CSV
    contact_points = parse_csv_contact_points(args.csv_file)

    if args.dry_run:
        print("DRY RUN - Contact points that would be created:")
        for cp in contact_points:
            print(json.dumps(cp, indent=2))
        return

    # Initialize client
    client = GrafanaProvisioningClient(
        grafana_server=args.grafana_server,
        username=args.username,
        password=args.password
    )

    # Sync contact points
    sync_contact_points(client, contact_points, replace_all=args.replace_all)

    print("\nContact points sync completed!")


if __name__ == "__main__":
    main()