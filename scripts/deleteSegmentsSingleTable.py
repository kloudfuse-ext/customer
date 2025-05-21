#!/usr/bin/env python3

import argparse
import json
import os
import requests
import sys
from typing import List, Dict, Any, Optional

def extract_segments(response_data: Dict[str, Any]) -> List[str]:
    """
    Extract segment names from the Pinot query response
    
    Args:
        response_data: The JSON response from Pinot query
        
    Returns:
        List of segment names
    """
    segments = []
    
    # Check if response has the expected structure
    if 'resultTable' in response_data and 'rows' in response_data['resultTable']:
        rows = response_data['resultTable']['rows']
        
        # Each row should be a list with a single string (segment name)
        for row in rows:
            if isinstance(row, list) and len(row) > 0:
                segment_name = row[0]
                if segment_name.startswith('kf_'):
                    segments.append(segment_name)
    
    return segments

def main():
    """
    Main function for the Pinot Segment Cleanup Tool - Single Table Version
    """
    parser = argparse.ArgumentParser(description='Apache Pinot Segment Cleanup Tool - Single Table Version')
    parser.add_argument('--host', default='localhost', help='Pinot controller host (default: localhost)')
    parser.add_argument('--port', default='9000', help='Pinot controller port (default: 9000)')
    parser.add_argument('--broker-port', default='8099', help='Pinot broker port (default: 8099)')
    parser.add_argument('--where', required=True, help='Any condition for segment metadata (e.g. "expiry > 0")')
    parser.add_argument('--table', required=True, help='Name of the table to process')
    parser.add_argument('--dry-run', action='store_true', help='List segments but don\'t delete them')
    parser.add_argument('--debug', action='store_true', help='Enable debug output (show raw responses)')
    
    args = parser.parse_args()
    
    # Ensure proper spacing in WHERE clause
    where_clause = args.where
    table_name = args.table
    
    print("=" * 70)
    print("Apache Pinot Segment Cleanup Tool - Single Table Version")
    print("=" * 70)
    print(f"Controller: {args.host}:{args.port}")
    print(f"Broker: {args.host}:{args.broker_port}")
    print(f"Table: {table_name}")
    print(f"WHERE Clause: {where_clause}")
    print(f"Mode: {'DRY RUN (will not delete segments)' if args.dry_run else 'LIVE (will delete matching segments)'}")
    if args.debug:
        print(f"Debug mode: ENABLED")
    print("=" * 70)
    
    # Test connection to controller and broker
    print("Testing connection to Pinot controller...")
    try:
        response = requests.get(f"http://{args.host}:{args.port}/", timeout=5)
        if response.status_code != 200:
            print(f"Error: Received status code {response.status_code} from controller")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not connect to Pinot controller at {args.host}:{args.port}")
        print(f"Exception: {e}")
        print("You may need to set up port forwarding: kubectl port-forward service/pinot-controller 9000:9000")
        sys.exit(1)
    
    print("Testing connection to Pinot broker...")
    try:
        response = requests.get(f"http://{args.host}:{args.broker_port}/", timeout=5)
        # Even if we get a 404, we'll consider it a success as the service might be running
        # but not have a root endpoint
        if response.status_code >= 500:
            print(f"Warning: Received status code {response.status_code} from broker")
            print("Continuing anyway, but queries may fail if the broker is not accessible.")
    except requests.exceptions.RequestException as e:
        print(f"Warning: Could not connect to Pinot broker at {args.host}:{args.broker_port}")
        print(f"Exception: {e}")
        print("You may need to set up port forwarding: kubectl port-forward service/pinot-broker 8099:8099")
        print("Continuing anyway, but queries may fail if the broker is not accessible.")
    
    print("Successfully connected to Pinot controller, proceeding with broker queries...")
    print("=" * 70)
    
    # Process the specified table
    print(f"Processing table: {table_name}")
    
    # Execute SQL query to get segment names
    sql_query = f'SELECT $segmentName FROM "{table_name}" WHERE {where_clause}'
    print(f"  Executing query: {sql_query}")
    
    query_url = f"http://{args.host}:{args.broker_port}/query/sql"
    query_payload = {
        "sql": sql_query,
        "trace": False,
        "queryOptions": ""
    }
    
    # Display curl equivalent only in debug mode
    if args.debug:
        print(f"  Curl equivalent: curl -s -X POST \"{query_url}\" -H \"Content-Type: application/json\" -d '{json.dumps(query_payload)}'")
    
    try:
        query_response = requests.post(query_url, json=query_payload, timeout=15)
        print("  Query executed successfully.")
        
        # Pretty print the response for debugging only if debug mode is enabled
        try:
            response_json = query_response.json()
            
            if args.debug:
                print("  Raw response:")
                response_str = json.dumps(response_json, indent=2)
                print(response_str[:1000])  # Print first 1000 chars to avoid too much output
                if len(response_str) > 1000:
                    print("  ... (response truncated for readability)")
        except json.JSONDecodeError:
            print(f"  Could not parse response as JSON: {query_response.text}")
            print(f"  Skipping table {table_name}.")
            sys.exit(1)
        
        # Extract segments from the response
        print("  Extracting segments from response...")
        segments = extract_segments(response_json)
        
        if not segments:
            print("  No segments found matching criteria.")
            print(f"  Exiting as there is nothing to process for {table_name}.")
            sys.exit(0)
        
        print(f"  Successfully extracted {len(segments)} segments.")
        print("  First few segments:")
        for segment in segments[:5]:
            print(f"    - {segment}")
        
        if len(segments) > 5:
            print(f"    ... and {len(segments) - 5} more segments")
        
        # If dry run, skip deletion
        if args.dry_run:
            print(f"  DRY RUN: Skipping deletion for table {table_name}")
            print("=" * 70)
            print("Summary:")
            print(f"Table processed: {table_name}")
            print(f"Segments found: {len(segments)}")
            print("DRY RUN: No segments were deleted")
            sys.exit(0)
        
        # Ask for confirmation before deleting
        confirmation = input(f"  Are you sure you want to delete these {len(segments)} segments from {table_name}? (y/n): ")
        if not confirmation.lower().startswith('y'):
            print(f"  User cancelled deletion. Exiting.")
            sys.exit(0)
        
        # Delete segments
        print(f"  Deleting segments from table {table_name}...")
        success_count = 0
        failure_count = 0
        
        for segment in segments:
            delete_url = f"http://{args.host}:{args.port}/segments/{table_name}/{segment}"
            print(f"    Deleting segment: {segment}")
            
            try:
                delete_response = requests.delete(delete_url)
                response_data = delete_response.json()
                
                # Check for success
                if (response_data.get('status') == 'success' or 
                    response_data.get('status') == 'Segment deleted'):
                    print(f"    Successfully deleted segment: {segment}")
                    success_count += 1
                else:
                    print(f"    Failed to delete segment: {segment}")
                    print(f"    Response: {delete_response.text}")
                    failure_count += 1
            except Exception as e:
                print(f"    Error deleting segment {segment}: {e}")
                failure_count += 1
        
        print(f"  Deletion for table {table_name} complete.")
        print(f"  Successfully deleted: {success_count} segments")
        print(f"  Failed to delete: {failure_count} segments")
        
        # Print summary
        print("=" * 70)
        print("Summary:")
        print(f"Table processed: {table_name}")
        print(f"Segments deleted: {success_count}")
        print(f"Segments failed to delete: {failure_count}")
        
        sys.exit(1 if failure_count > 0 else 0)
            
    except Exception as e:
        print(f"  Error executing query: {e}")
        print(f"  Exiting.")
        sys.exit(1)

if __name__ == "__main__":
    main()