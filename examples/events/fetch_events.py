#!/usr/bin/env python3
"""
fetch_events.py — Fetch raw events from Kloudfuse using the events query.

Uses the `events` GraphQL query against the events-query-service endpoint
(/events-query, distinct from the /query endpoint used for logs and metrics).
Paginates with `offset` since `events` has no cursor.

Facet names (top-level event fields) must be prefixed with `@` in a filter,
e.g. `@severity` or `@source`. Label names (source-specific metadata) are
used bare, e.g. `kube_namespace`. See reference/api/events.adoc.

Usage:
    python3 fetch_events.py --filter '{"eq": {"name": "@severity", "value": "error"}}'
    python3 fetch_events.py --filter '{"eq": {"name": "@source", "value": "kubernetes"}}' --minutes 30
    python3 fetch_events.py --output events.jsonl --max-rows 500
    python3 fetch_events.py --help
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

GRAPHQL_QUERY = """
{
  events(
    timestamp: %(timestamp)s
    durationSecs: %(duration_secs)s
    filter: %(filter)s
    offset: %(offset)s
    limit: %(limit)s
    sortBy: %(sort_by)s
    sortOrder: %(sort_order)s
  ) {
    id
    title
    text
    severity
    source
    eventType
    aggregationKey
    host
    priority
    timestamp
    labels { name value }
  }
}
"""

PAGE_SIZE = 200


def json_filter_to_graphql(value) -> str:
    """Convert a parsed JSON EventFilter into GraphQL object-literal syntax.

    JSON requires quoted keys ("eq": ...); GraphQL input object literals require
    bare keys (eq: ...). --filter is accepted as JSON for shell-quoting convenience
    and readability, then converted here before being spliced into the query.
    """
    if isinstance(value, dict):
        parts = [f"{k}: {json_filter_to_graphql(v)}" for k, v in value.items()]
        return "{" + ", ".join(parts) + "}"
    if isinstance(value, list):
        return "[" + ", ".join(json_filter_to_graphql(v) for v in value) + "]"
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(value)


def fetch_page(host: str, token: str, timestamp: str, duration_secs: int,
               event_filter: str, offset: int, limit: int, sort_by: str, sort_order: str) -> list:
    payload = {
        "query": GRAPHQL_QUERY % {
            "timestamp": json.dumps(timestamp),
            "duration_secs": duration_secs,
            "filter": event_filter,
            "offset": offset,
            "limit": limit,
            "sort_by": sort_by,
            "sort_order": sort_order,
        }
    }
    resp = requests.post(
        f"https://{host}/events-query",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()

    if "errors" in body:
        for err in body["errors"]:
            print(f"GraphQL error: {err['message']}", file=sys.stderr)
        sys.exit(1)

    return body["data"]["events"] or []


def fetch_all(host: str, token: str, timestamp: str, duration_secs: int, event_filter: str,
              sort_by: str, sort_order: str, max_rows, output) -> None:
    offset = 0
    total = 0
    page = 0

    while True:
        page += 1
        print(f"Fetching page {page} (offset={offset}) …", file=sys.stderr)

        events = fetch_page(host, token, timestamp, duration_secs, event_filter,
                             offset, PAGE_SIZE, sort_by, sort_order)

        for event in events:
            if max_rows is not None and total >= max_rows:
                break
            output.write(json.dumps(event) + "\n")
            total += 1

        print(f"  → {len(events)} row(s) (total so far: {total})", file=sys.stderr)

        if max_rows is not None and total >= max_rows:
            print(f"Reached --max-rows {max_rows}, stopping.", file=sys.stderr)
            break

        if len(events) < PAGE_SIZE:
            print("End of results.", file=sys.stderr)
            break

        offset += PAGE_SIZE

    print(f"\nDone — {total} row(s) written.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch raw events from Kloudfuse.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--filter", default="{}", help="EventFilter as a JSON object (default: no filter)")
    parser.add_argument("--minutes", type=int, default=60, help="Look-back window in minutes (default: 60)")
    parser.add_argument("--timestamp", help="End timestamp (RFC 3339), overrides --minutes; window looks back from here")
    parser.add_argument("--sort-by", default="TIMESTAMP",
                         choices=["TIMESTAMP", "SOURCE", "EVENT_ID", "AGGREGATION_KEY", "SEVERITY", "EVENT_TYPE", "TITLE"])
    parser.add_argument("--sort-order", default="Desc", choices=["Asc", "Desc"])
    parser.add_argument("--max-rows", type=int, default=None, help="Stop after this many rows")
    parser.add_argument("--output", help="Write JSON Lines to this file (default: stdout)")
    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        sys.exit(1)

    try:
        filter_gql = json_filter_to_graphql(json.loads(args.filter))
    except json.JSONDecodeError as e:
        print(f"Error: --filter is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(tz=timezone.utc)
    timestamp = args.timestamp or now.strftime("%Y-%m-%dT%H:%M:%SZ")
    duration_secs = args.minutes * 60

    print(f"Host     : {args.host}", file=sys.stderr)
    print(f"Filter   : {args.filter}", file=sys.stderr)
    print(f"Range    : last {args.minutes}m ending {timestamp}", file=sys.stderr)
    if args.max_rows:
        print(f"Max rows : {args.max_rows}", file=sys.stderr)
    print(file=sys.stderr)

    if args.output:
        with open(args.output, "w") as f:
            fetch_all(args.host, args.token, timestamp, duration_secs, filter_gql,
                      args.sort_by, args.sort_order, args.max_rows, f)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        fetch_all(args.host, args.token, timestamp, duration_secs, filter_gql,
                  args.sort_by, args.sort_order, args.max_rows, sys.stdout)


if __name__ == "__main__":
    main()
