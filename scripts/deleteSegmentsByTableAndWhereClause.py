#!/usr/bin/env python3

import argparse
import json
import requests
import sys

def make_request(url, method='GET', json_data=None, params=None, timeout=5, debug=False):
    """Make HTTP request with error handling"""
    try:
        if method == 'GET':
            response = requests.get(url, timeout=timeout)
        elif method == 'POST':
            response = requests.post(url, json=json_data, timeout=timeout)
        elif method == 'DELETE':
            if debug:
                print("Making DELETE request to: {}".format(url))
                print("Query parameters: {}".format(json.dumps(params, indent=2)))
            response = requests.delete(url, params=params, timeout=timeout)
        else:
            raise ValueError("Unsupported HTTP method: {}".format(method))

        if response.status_code >= 500:
            print("Error: Server error (status code {})".format(response.status_code))
            sys.exit(1)
        return response
    except requests.exceptions.RequestException as e:
        print("Error: Request failed - {}".format(e))
        sys.exit(1)

def get_existing_tables(host, port):
    """Get list of existing tables from Pinot controller"""
    response = make_request("http://{}:{}/tables".format(host, port))
    tables_data = response.json()

    if not isinstance(tables_data, dict) or "tables" not in tables_data:
        print("Error: Unexpected response format from controller")
        print("Response: {}".format(tables_data))
        sys.exit(1)

    return set(tables_data["tables"])

def validate_tables(args):
    """Validate that all specified tables exist in Pinot"""
    print("Validating table names...")
    existing_tables = get_existing_tables(args.host, args.port)

    invalid_tables = set(args.tables) - existing_tables
    if invalid_tables:
        print("\nError: The following tables do not exist in Pinot:")
        for table in sorted(invalid_tables):
            print("  - {}".format(table))
        print("\nAvailable tables:")
        for table in sorted(existing_tables):
            print("  - {}".format(table))
        sys.exit(1)

    print("All {} specified tables exist in Pinot.".format(len(args.tables)))

def extract_segments(response_data):
    """Extract segment names from the Pinot query response"""
    segments = []

    if 'resultTable' in response_data and 'rows' in response_data['resultTable']:
        for row in response_data['resultTable']['rows']:
            if isinstance(row, list) and row:
                segments.append(row[0])

    return sorted(segments)

def get_table_types(host, port, table_name, debug=False):
    """Get the types (OFFLINE/REALTIME) for a given table"""
    response = make_request("http://{}:{}/tables/{}".format(host, port, table_name))
    table_info = response.json()

    types = []
    if isinstance(table_info, dict):
        if "OFFLINE" in table_info:
            types.append("OFFLINE")
        if "REALTIME" in table_info:
            types.append("REALTIME")

    if debug:
        print("  Table info response: {}".format(json.dumps(table_info, indent=2)))

    return types

def delete_segments_for_type(args, table_name, table_type, segments):
    """Delete segments for a specific table type"""
    print("\n  Processing {} segments for table: {}".format(table_type, table_name))

    delete_url = "http://{}:{}/segments/{}".format(args.host, args.port, table_name)
    params = {
        'type': table_type,
        'segments': segments
    }

    if args.debug:
        print("    Delete URL: {}".format(delete_url))
        print("    Query parameters: {}".format(json.dumps(params, indent=2)))

    response = make_request(delete_url, method='DELETE', params=params, timeout=30, debug=args.debug)

    if args.debug:
        print("    Response status code: {}".format(response.status_code))
        print("    Response headers: {}".format(dict(response.headers)))
        print("    Response text: {}".format(response.text))

    if response.status_code in [200, 204]:
        print("    Successfully deleted {} segments from {} ({})".format(len(segments), table_name, table_type))
        return len(segments), 0
    else:
        print("    Failed to delete segments from {} ({})".format(table_name, table_type))
        print("    Status code: {}".format(response.status_code))
        print("    Response: {}".format(response.text))
        return 0, len(segments)

def process_table(args, table_name):
    """Process a single table and return success and failure counts"""
    print("\nProcessing table: {}".format(table_name))

    table_types = get_table_types(args.host, args.port, table_name, args.debug)
    if not table_types:
        print("  Error: Table {} not found in either OFFLINE or REALTIME format".format(table_name))
        return 0, 0

    print("  Found table in formats: {}".format(', '.join(table_types)))

    sql_query = 'SELECT DISTINCT $segmentName FROM "{}" WHERE {}'.format(table_name, args.where)
    print("  Executing query: {}".format(sql_query))

    query_url = "http://{}:{}/query/sql".format(args.host, args.broker_port)
    query_payload = {"sql": sql_query, "trace": False, "queryOptions": ""}

    if args.debug:
        print("  Curl equivalent: curl -s -X POST \"{}\" -H \"Content-Type: application/json\" -d '{}'".format(query_url, json.dumps(query_payload)))

    response = make_request(query_url, method='POST', json_data=query_payload, timeout=15)
    print("  Query executed successfully.")

    try:
        response_json = response.json()
        if args.debug:
            print("  Raw response:")
            print(json.dumps(response_json, indent=2)[:1000])
    except json.JSONDecodeError:
        print("  Could not parse response as JSON: {}".format(response.text))
        return 0, 0

    segments = extract_segments(response_json)
    if not segments:
        print("  No segments found matching criteria.")
        return 0, 0

    print("  Found {} segments:".format(len(segments)))
    for segment in segments[:5]:
        print("    - {}".format(segment))
    if len(segments) > 5:
        print("    ... and {} more segments".format(len(segments) - 5))

    if args.dry_run:
        print("  DRY RUN: Skipping deletion for table {}".format(table_name))
        return 0, 0

    confirmation = input("  Are you sure you want to delete these {} segments from {}? (y/n): ".format(len(segments), table_name))
    if not confirmation.lower().startswith('y'):
        print("  User cancelled deletion. Skipping table {}.".format(table_name))
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
        print("Tables provided: {}".format(len(args.tables)))
        print("WHERE clauses provided: {}".format(len(args.where)))
        sys.exit(1)

    print("=" * 70)
    print("Apache Pinot Segment Cleanup Tool - Multi Table Version")
    print("=" * 70)
    print("Controller: {}:{}".format(args.host, args.port))
    print("Broker: {}:{}".format(args.host, args.broker_port))
    print("Tables and their WHERE clauses:")
    for table, where_clause in zip(args.tables, args.where):
        print("  - {}: {}".format(table, where_clause))
    print("Mode: {}".format('DRY RUN (will not delete segments)' if args.dry_run else 'LIVE (will delete matching segments)'))
    if args.debug:
        print("Debug mode: ENABLED")
    print("=" * 70)

    # Test connections
    make_request("http://{}:{}/".format(args.host, args.port))
    make_request("http://{}:{}/".format(args.host, args.broker_port))
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
        print("Table: {}".format(table_name))
        print("  Segments deleted: {}".format(success_count))
        print("  Segments failed to delete: {}".format(failure_count))
    print("-" * 70)
    print("Total segments deleted: {}".format(total_success))
    print("Total segments failed to delete: {}".format(total_failure))

    sys.exit(1 if total_failure > 0 else 0)

if __name__ == "__main__":
    main()