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
    Main function for the Pinot Segment Cleanup Tool
    """
    parser = argparse.ArgumentParser(description='Apache Pinot Segment Cleanup Tool')
    parser.add_argument('--host', default='localhost', help='Pinot controller host (default: localhost)')
    parser.add_argument('--port', default='9000', help='Pinot controller port (default: 9000)')
    parser.add_argument('--broker-port', default='8099', help='Pinot broker port (default: 8099)')
    parser.add_argument('--where', required=True, help='Any condition for segment metadata (e.g. "expiry > 0")')
    parser.add_argument('--dry-run', action='store_true', help='List segments but don\'t delete them')
    parser.add_argument('--debug', action='store_true', help='Enable debug output (show raw responses)')
    
    args = parser.parse_args()
    
    # Ensure proper spacing in WHERE clause
    where_clause = args.where
    
    print("=" * 70)
    print("Apache Pinot Segment Cleanup Tool (Python Version)")
    print("=" * 70)
    print(f"Controller: {args.host}:{args.port}")
    print(f"Broker: {args.host}:{args.broker_port}")
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
    
    # Get all tables
    tables_url = f"http://{args.host}:{args.port}/tables"
    try:
        tables_response = requests.get(tables_url, timeout=10)
        tables_data = tables_response.json()
        all_tables = tables_data.get('tables', [])
    except Exception as e:
        print(f"Error retrieving tables: {e}")
        print("Using default table list.")
        all_tables = ["kf_events", "kf_logs", "kf_logs_views", "kf_metrics", "kf_traces", "kf_traces_errors"]
    
    if not all_tables:
        print("No tables found or error retrieving tables. Using default table list.")
        all_tables = ["kf_events", "kf_logs", "kf_logs_views", "kf_metrics", "kf_traces", "kf_traces_errors"]
    
    print("Found tables:")
    for table in all_tables:
        print(f"  {table}")
    print("=" * 70)
    
    # Process each table
    total_tables = len(all_tables)
    processed_tables = 0
    total_segments_deleted = 0
    total_segments_failed = 0
    
    for table in all_tables:
        print(f"Processing table: {table}")
        
        # Execute SQL query to get segment names
        sql_query = f'SELECT $segmentName FROM "{table}" WHERE {where_clause}'
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
                print("  Skipping table.")
                continue
            
            # Extract segments from the response
            print("  Extracting segments from response...")
            segments = extract_segments(response_json)
            
            if not segments:
                print("  No segments found matching criteria.")
                print(f"  Skipping table {table}.")
                continue
            
            print(f"  Successfully extracted {len(segments)} segments.")
            print("  First few segments:")
            for segment in segments[:5]:
                print(f"    - {segment}")
            
            if len(segments) > 5:
                print(f"    ... and {len(segments) - 5} more segments")
            
            # If dry run, skip deletion
            if args.dry_run:
                print(f"  DRY RUN: Skipping deletion for table {table}")
                processed_tables += 1
                continue
            
            # Ask for confirmation before deleting
            confirmation = input(f"  Are you sure you want to delete these segments from {table}? (y/n): ")
            if not confirmation.lower().startswith('y'):
                print(f"  Skipping table {table}...")
                continue
            
            # Delete segments
            print(f"  Deleting segments from table {table}...")
            success_count = 0
            failure_count = 0
            
            for segment in segments:
                delete_url = f"http://{args.host}:{args.port}/segments/{table}/{segment}"
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
            
            print(f"  Deletion for table {table} complete.")
            print(f"  Successfully deleted: {success_count} segments")
            print(f"  Failed to delete: {failure_count} segments")
            
            total_segments_deleted += success_count
            total_segments_failed += failure_count
                
        except Exception as e:
            print(f"  Error executing query: {e}")
            print(f"  Skipping table {table}.")
            continue
        
        processed_tables += 1
        print("=" * 70)
    
    # Print summary
    print("Summary:")
    print(f"Total tables found: {total_tables}")
    print(f"Tables processed: {processed_tables}")
    print(f"Total segments deleted: {total_segments_deleted}")
    print(f"Total segments failed to delete: {total_segments_failed}")
    
    if args.dry_run:
        print("DRY RUN: No segments were actually deleted")
    
    sys.exit(1 if total_segments_failed > 0 else 0)

if __name__ == "__main__":
    main()