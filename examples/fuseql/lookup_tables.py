#!/usr/bin/env python3
"""
lookup_tables.py — Manage FuseQL lookup tables in Kloudfuse.

Lookup tables are used with the FuseQL `lookup` operator to enrich log rows
at query time. This script provides list, create, and delete operations.

Usage:
    python3 lookup_tables.py list
    python3 lookup_tables.py create --name cluster_costs --primary-key ClusterName --file cluster_costs.csv
    python3 lookup_tables.py delete --name cluster_costs
    python3 lookup_tables.py --help
"""

import argparse
import json
import os
import sys

import requests

ENDPOINT = "/query"


def graphql(host: str, token: str, query: str, variables=None) -> dict:
    payload: dict = {"query": query}
    if variables:
        payload["variables"] = variables

    resp = requests.post(
        f"https://{host}{ENDPOINT}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=60,
    )
    resp.raise_for_status()
    body = resp.json()

    if "errors" in body:
        for err in body["errors"]:
            print(f"GraphQL error: {err['message']}", file=sys.stderr)
        sys.exit(1)

    return body["data"]


def cmd_list(host: str, token: str, args: argparse.Namespace) -> None:
    data = graphql(
        host, token,
        "query { getLookUpTables { TableName Dimensions { Name DataType } PrimaryKeyColumns FolderUid } }"
    )
    tables = data.get("getLookUpTables") or []

    if not tables:
        print("No lookup tables found.")
        return

    for t in tables:
        print(f"\nTable   : {t['TableName']}")
        print(f"  Primary keys : {', '.join(t['PrimaryKeyColumns'])}")
        if t.get("FolderUid"):
            print(f"  Folder UID   : {t['FolderUid']}")
        print("  Columns:")
        for dim in t.get("Dimensions") or []:
            print(f"    {dim['Name']} ({dim['DataType']})")

    print(f"\n{len(tables)} table(s) found.")


def cmd_create(host: str, token: str, args: argparse.Namespace) -> None:
    if not os.path.isfile(args.file):
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        sys.exit(1)

    # Infer dimensions from CSV header
    with open(args.file) as f:
        header_line = f.readline().strip()

    columns = [c.strip() for c in header_line.split(",")]
    if not columns:
        print("Error: CSV file has no header row", file=sys.stderr)
        sys.exit(1)

    # Determine data types: default STRING, allow overrides via --types col:TYPE,...
    type_map: dict[str, str] = {}
    if args.types:
        for pair in args.types.split(","):
            col, dtype = pair.strip().split(":", 1)
            type_map[col.strip()] = dtype.strip().upper()

    dimensions = [{"Name": col, "DataType": type_map.get(col, "STRING")} for col in columns]

    print(f"Creating table '{args.name}' from {args.file}")
    print(f"  Columns      : {', '.join(col['Name'] for col in dimensions)}")
    print(f"  Primary keys : {args.primary_key}")
    type_summary = ", ".join(f"{d['Name']}:{d['DataType']}" for d in dimensions)
    print(f"  Data types   : {type_summary}")

    mutation = """
    mutation($tableName: String!, $dimensions: [NameAndDataTypeInput!]!, $file: Upload!, $primaryKeyColumns: [String!]!, $folderUid: String) {
      createDimensionTable(tableName: $tableName, dimensions: $dimensions, file: $file, primaryKeyColumns: $primaryKeyColumns, folderUid: $folderUid)
    }
    """
    variables = {
        "tableName": args.name,
        "dimensions": dimensions,
        "primaryKeyColumns": [k.strip() for k in args.primary_key.split(",")],
        "file": None,
        "folderUid": args.folder_uid or None,
    }

    with open(args.file, "rb") as f:
        resp = requests.post(
            f"https://{host}{ENDPOINT}",
            headers={"Authorization": f"Bearer {token}"},
            files={
                "operations": (None, json.dumps({"query": mutation, "variables": variables})),
                "map": (None, '{"0": ["variables.file"]}'),
                "0": (os.path.basename(args.file), f, "text/csv"),
            },
            timeout=120,
        )

    resp.raise_for_status()
    body = resp.json()

    if "errors" in body:
        for err in body["errors"]:
            print(f"GraphQL error: {err['message']}", file=sys.stderr)
        sys.exit(1)

    success = body["data"].get("createDimensionTable")
    if success:
        print(f"Table '{args.name}' created successfully.")
    else:
        print(f"Table creation returned: {success}", file=sys.stderr)
        sys.exit(1)


def cmd_delete(host: str, token: str, args: argparse.Namespace) -> None:
    confirm = input(f"Delete lookup table '{args.name}'? This cannot be undone. [y/N] ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return

    data = graphql(
        host, token,
        f'mutation {{ deleteDimensionTable(tableName: {json.dumps(args.name)}) }}'
    )
    success = data.get("deleteDimensionTable")
    if success:
        print(f"Table '{args.name}' deleted.")
    else:
        print(f"Delete returned: {success}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage Kloudfuse FuseQL lookup tables.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="List all lookup tables")

    p_create = sub.add_parser("create", help="Create a lookup table from a CSV file")
    p_create.add_argument("--name", required=True, help="Table name")
    p_create.add_argument("--file", required=True, help="Path to CSV file")
    p_create.add_argument("--primary-key", required=True,
                          help="Comma-separated primary key column name(s)")
    p_create.add_argument("--types",
                          help="Override data types: col:TYPE,col:TYPE (e.g. Cost:DOUBLE,Count:INTEGER). "
                               "Default type is STRING.")
    p_create.add_argument("--folder-uid", help="Optional folder UID to place the table in")

    p_delete = sub.add_parser("delete", help="Delete a lookup table")
    p_delete.add_argument("--name", required=True, help="Table name to delete")

    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        sys.exit(1)

    dispatch = {"list": cmd_list, "create": cmd_create, "delete": cmd_delete}
    dispatch[args.command](args.host, args.token, args)


if __name__ == "__main__":
    main()
