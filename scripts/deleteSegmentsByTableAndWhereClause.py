#!/usr/bin/env python3

import argparse
import json
import requests
import sys
from typing import List, Dict, Any, Set, Tuple

def make_request(url: str, method: str = 'GET', json_data: Dict = None, params: Dict = None, timeout: int = 5) -> requests.Response:
    """Make HTTP request with error handling"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, json=json_data, timeout=timeout)
        elif method == 'DELETE':
            response = requests.delete(url, params=params, timeout=timeout)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
            
        if response.status_code >= 500:
            print(f"Error: Server error (status code {response.status_code})")
            sys.exit(1)
        return response
    except requests.exceptions.RequestException as e:
        print(f"Error: Request failed - {e}")
        sys.exit(1)

def get_existing_tables(host: str, port: str) -> Set[str]:
    """Get list of existing tables from Pinot controller"""
    response = make_request(f"http://{host}:{port}/tables")
    tables_data = response.json()
    
    if not isinstance(tables_data, dict) or "tables" not in tables_data:
        print("Error: Unexpected response format from controller")
        print(f"Response: {tables_data}")
        sys.exit(1)
        
    return set(tables_data["tables"])

def validate_tables(args) -> None:
    """Validate that all specified tables exist in Pinot"""
    print("Validating table names...")
    existing_tables = get_existing_tables(args.host, args.port)
    
    invalid_tables = set(args.tables) - existing_tables
    if invalid_tables:
        print("\nError: The following tables do not exist in Pinot:")
        for table in sorted(invalid_tables):
            print(f"  - {table}")
        print("\nAvailable tables:")
        for table in sorted(existing_tables):
            print(f"  - {table}")
        sys.exit(1)
    
    print(f"All {len(args.tables)} specified tables exist in Pinot.")

def extract_segments(response_data: Dict[str, Any]) -> List[str]:
    """Extract segment names from the Pinot query response"""
    segments = set()
    
    if 'resultTable' in response_data and 'rows' in response_data['resultTable']:
        for row in response_data['resultTable']['rows']:
            if isinstance(row, list) and row and row[0].startswith('kf_'):
                segments.add(row[0])
    
    return sorted(list(segments))

def get_table_types(host: str, port: str, table_name: str, debug: bool = False) -> List[str]:
    """Get the types (OFFLINE/REALTIME) for a given table"""
    response = make_request(f"http://{host}:{port}/tables/{table_name}")
    table_info = response.json()
    
    types = []
    if isinstance(table_info, dict):
        if "OFFLINE" in table_info:
            types.append("OFFLINE")
        if "REALTIME" in table_info:
            types.append("REALTIME")
            
    if debug:
        print(f"  Table info response: {json.dumps(table_info, indent=2)}")
        
    return types

def delete_segments_for_type(args, table_name: str, table_type: str, segments: List[str]) -> Tuple[int, int]:
    """Delete segments for a specific table type"""
    print(f"\n  Processing {table_type} segments for table: {table_name}")
    
    delete_url = f"http://{args.host}:{args.port}/segments/{table_name}_{table_type}"
    params = {'type': table_type}
    for segment in segments:
        params['segments'] = segment
    
    if args.debug:
        print(f"    Delete URL: {delete_url}")
        print(f"    Parameters: {params}")
    
    response = make_request(delete_url, method='DELETE', params=params, timeout=30)
    
    if args.debug:
        print(f"    Response status code: {response.status_code}")
        print(f"    Response headers: {dict(response.headers)}")
        print(f"    Response text: {response.text}")
    
    if response.status_code in [200, 204]:
        print(f"    Successfully deleted {len(segments)} segments from {table_name} ({table_type})")
        return len(segments), 0
    else:
        print(f"    Failed to delete segments from {table_name} ({table_type})")
        print(f"    Status code: {response.status_code}")
        print(f"    Response: {response.text}")
        return 0, len(segments)

def process_table(args, table_name: str) -> Tuple[int, int]:
    """Process a single table and return success and failure counts"""
    print(f"\nProcessing table: {table_name}")
    
    table_types = get_table_types(args.host, args.port, table_name, args.debug)
    if not table_types:
        print(f"  Error: Table {table_name} not found in either OFFLINE or REALTIME format")
        return 0, 0
    
    print(f"  Found table in formats: {', '.join(table_types)}")
    
    sql_query = f'SELECT $segmentName FROM "{table_name}" WHERE {args.where}'
    print(f"  Executing query: {sql_query}")
    
    query_url = f"http://{args.host}:{args.broker_port}/query/sql"
    query_payload = {"sql": sql_query, "trace": False, "queryOptions": ""}
    
    if args.debug:
        print(f"  Curl equivalent: curl -s -X POST \"{query_url}\" -H \"Content-Type: application/json\" -d '{json.dumps(query_payload)}'")
    
    response = make_request(query_url, method='POST', json_data=query_payload, timeout=15)
    print("  Query executed successfully.")
    
    try:
        response_json = response.json()
        if args.debug:
            print("  Raw response:")
            print(json.dumps(response_json, indent=2)[:1000])
    except json.JSONDecodeError:
        print(f"  Could not parse response as JSON: {response.text}")
        return 0, 0
    
    segments = extract_segments(response_json)
    if not segments:
        print("  No segments found matching criteria.")
        return 0, 0
    
    print(f"  Found {len(segments)} segments:")
    for segment in segments[:5]:
        print(f"    - {segment}")
    if len(segments) > 5:
        print(f"    ... and {len(segments) - 5} more segments")
    
    if args.dry_run:
        print(f"  DRY RUN: Skipping deletion for table {table_name}")
        return 0, 0
    
    confirmation = input(f"  Are you sure you want to delete these {len(segments)} segments from {table_name}? (y/n): ")
    if not confirmation.lower().startswith('y'):
        print(f"  User cancelled deletion. Skipping table {table_name}.")
        return 0, 0
    
    total_success = total_failure = 0
    for table_type in table_types:
        success, failure = delete_segments_for_type(args, table_name, table_type, segments)
        total_success += success
        total_failure += failure
    
    return total_success, total_failure

def main():
    """Main function for the Pinot Segment Cleanup Tool - Multi Table Version"""
    parser = argparse.ArgumentParser(description='Apache Pinot Segment Cleanup Tool - Multi Table Version')
    parser.add_argument('--host', default='localhost', help='Pinot controller host (default: localhost)')
    parser.add_argument('--port', default='9000', help='Pinot controller port (default: 9000)')
    parser.add_argument('--broker-port', default='8099', help='Pinot broker port (default: 8099)')
    parser.add_argument('--tables', required=True, nargs='+', help='Names of the tables to process')
    parser.add_argument('--where', required=True, nargs='+', help='WHERE clauses for each table (must match number of tables)')
    parser.add_argument('--dry-run', action='store_true', help='List segments but don\'t delete them')
    parser.add_argument('--debug', action='store_true', help='Enable debug output (show raw responses)')
    
    args = parser.parse_args()
    
    if len(args.where) != len(args.tables):
        print("Error: Number of WHERE clauses must match number of tables")
        print(f"Tables provided: {len(args.tables)}")
        print(f"WHERE clauses provided: {len(args.where)}")
        sys.exit(1)
    
    print("=" * 70)
    print("Apache Pinot Segment Cleanup Tool - Multi Table Version")
    print("=" * 70)
    print(f"Controller: {args.host}:{args.port}")
    print(f"Broker: {args.host}:{args.broker_port}")
    print("Tables and their WHERE clauses:")
    for table, where_clause in zip(args.tables, args.where):
        print(f"  - {table}: {where_clause}")
    print(f"Mode: {'DRY RUN (will not delete segments)' if args.dry_run else 'LIVE (will delete matching segments)'}")
    if args.debug:
        print(f"Debug mode: ENABLED")
    print("=" * 70)
    
    # Test connections
    make_request(f"http://{args.host}:{args.port}/")
    make_request(f"http://{args.host}:{args.broker_port}/")
    print("Successfully connected to Pinot services")
    print("=" * 70)
    
    validate_tables(args)
    print("=" * 70)
    
    total_success = total_failure = 0
    table_results = []
    
    for table_name, where_clause in zip(args.tables, args.where):
        table_args = argparse.Namespace(**vars(args))
        table_args.where = where_clause
        success_count, failure_count = process_table(table_args, table_name)
        total_success += success_count
        total_failure += failure_count
        table_results.append((table_name, success_count, failure_count))
    
    print("\n" + "=" * 70)
    print("Summary:")
    for table_name, success_count, failure_count in table_results:
        print(f"Table: {table_name}")
        print(f"  Segments deleted: {success_count}")
        print(f"  Segments failed to delete: {failure_count}")
    print("-" * 70)
    print(f"Total segments deleted: {total_success}")
    print(f"Total segments failed to delete: {total_failure}")
    
    sys.exit(1 if total_failure > 0 else 0)

if __name__ == "__main__":
    main()