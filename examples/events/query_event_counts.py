#!/usr/bin/env python3
"""
query_event_counts.py — Aggregated event counts from Kloudfuse, optionally
grouped by facet/label and bucketed over time.

Uses the eventCounts GraphQL query against the events-query-service endpoint
(/events-query, distinct from the /query endpoint used for logs and metrics).

Facet names (top-level event fields) must be prefixed with `@` in a filter or
groupBys entry, e.g. `@severity` or `@source`. Label names (source-specific
metadata) are used bare, e.g. `kube_namespace`. See reference/api/events.adoc.

Usage:
    python3 query_event_counts.py --filter '{"eq": {"name": "@source", "value": "kubernetes"}}' \
        --group-by @severity --round-secs 300

    python3 query_event_counts.py --group-by @source --minutes 60

    python3 query_event_counts.py --help
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

GRAPHQL_QUERY = """
{
  eventCounts(
    timestamp: %(timestamp)s
    durationSecs: %(duration_secs)s
    filter: %(filter)s
    groupBys: %(group_bys)s
    roundSecs: %(round_secs)s
    limit: %(limit)s
  ) {
    timestamp
    count
    keys
    values
  }
}
"""


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


def run_query(host: str, token: str, timestamp: str, duration_secs: int, event_filter: str,
              group_bys: list, round_secs, limit: int) -> list:
    payload = {
        "query": GRAPHQL_QUERY % {
            "timestamp": json.dumps(timestamp),
            "duration_secs": duration_secs,
            "filter": event_filter,
            "group_bys": json.dumps(group_bys),
            "round_secs": "null" if round_secs is None else round_secs,
            "limit": limit,
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

    return body["data"]["eventCounts"] or []


def format_table(rows: list) -> None:
    if not rows:
        print("(no results)")
        return

    headers = ["timestamp", "keys", "values", "count"]
    formatted = []
    for row in rows:
        ts = row.get("timestamp")
        formatted.append([
            ts or "-",
            ",".join(row.get("keys") or []) or "-",
            ",".join(row.get("values") or []) or "-",
            str(row.get("count")),
        ])

    col_widths = [len(h) for h in headers]
    for row in formatted:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    print("  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers)))
    print("  ".join("-" * w for w in col_widths))
    for row in formatted:
        print("  ".join(v.ljust(col_widths[i]) for i, v in enumerate(row)))

    print(f"\n{len(rows)} row(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run an aggregated eventCounts query.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--filter", default="{}", help="EventFilter as a JSON object (default: no filter)")
    parser.add_argument("--group-by", dest="group_bys", action="append", default=[],
                         help="Facet (@-prefixed) or label to group by; repeatable")
    parser.add_argument("--round-secs", type=int, default=None,
                         help="Bucket size in seconds; omit to count over the full range as one bucket")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum rows to return (default: 1000)")
    parser.add_argument("--minutes", type=int, default=60, help="Look-back window in minutes (default: 60)")
    parser.add_argument("--timestamp", help="End timestamp (RFC 3339), overrides --minutes; window looks back from here")
    parser.add_argument("--json", dest="output_json", action="store_true", help="Print raw JSON result")
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
    print(f"Group by : {args.group_bys or '(none)'}", file=sys.stderr)
    print(f"Range    : last {args.minutes}m ending {timestamp}", file=sys.stderr)
    print(file=sys.stderr)

    rows = run_query(args.host, args.token, timestamp, duration_secs, filter_gql,
                      args.group_bys, args.round_secs, args.limit)

    if args.output_json:
        print(json.dumps(rows, indent=2))
    else:
        format_table(rows)


if __name__ == "__main__":
    main()
