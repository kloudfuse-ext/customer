#!/usr/bin/env python3
"""
fetch_logs.py — Fetch raw log rows from Kloudfuse using FuseQL and cursor pagination.

Uses getLogsWithFuseQlStream, which returns up to 200 rows per request.
Automatically follows the cursor until all matching logs are retrieved (or --max-rows is hit).

Note: window operators (accum, smooth, total, rollingstd) and aggregation operators
are not supported in this query — use query_log_metrics.py for those.

Usage:
    python3 fetch_logs.py --query 'level="error"'
    python3 fetch_logs.py --query 'source="grafana"' --minutes 30 --max-rows 500
    python3 fetch_logs.py --query 'level="error"' --output errors.jsonl
    python3 fetch_logs.py --help
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

GRAPHQL_QUERY = """
subscription {
  getLogsWithFuseQlStream(
    query: %(query)s
    startTs: %(start_ts)s
    endTs: %(end_ts)s
    cursor: %(cursor)s
  ) {
    ColumnHeaders
    TableResult
    Cursor
  }
}
"""


def fetch_page(host: str, token: str, fuseql: str, start_ts: str, end_ts: str, cursor) -> dict:
    payload = {
        "query": GRAPHQL_QUERY % {
            "query": json.dumps(fuseql),
            "start_ts": json.dumps(start_ts),
            "end_ts": json.dumps(end_ts),
            "cursor": json.dumps(cursor),
        }
    }
    resp = requests.post(
        f"https://{host}/query",
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

    return body["data"]["getLogsWithFuseQlStream"]


def fetch_all(host: str, token: str, fuseql: str, start_ts: str, end_ts: str,
              max_rows, output) -> None:
    cursor = None
    total = 0
    headers = None
    page = 0

    while True:
        page += 1
        print(f"Fetching page {page} (cursor={'null' if cursor is None else cursor[:16] + '…'}) …",
              file=sys.stderr)

        result = fetch_page(host, token, fuseql, start_ts, end_ts, cursor)
        rows = result.get("TableResult") or []

        if headers is None:
            headers = result.get("ColumnHeaders") or []

        for row in rows:
            if max_rows is not None and total >= max_rows:
                break
            record = dict(zip(headers, row))
            # Convert epoch-ms timestamp to ISO 8601
            if "timestamp" in record and isinstance(record["timestamp"], (int, float)):
                record["timestamp"] = datetime.fromtimestamp(
                    record["timestamp"] / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
            output.write(json.dumps(record) + "\n")
            total += 1

        print(f"  → {len(rows)} rows (total so far: {total})", file=sys.stderr)

        if max_rows is not None and total >= max_rows:
            print(f"Reached --max-rows {max_rows}, stopping.", file=sys.stderr)
            break

        next_cursor = result.get("Cursor", "")
        if not next_cursor:
            print("End of results.", file=sys.stderr)
            break

        cursor = next_cursor

    print(f"\nDone — {total} row(s) written.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch raw log rows from Kloudfuse with FuseQL.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--query", required=True, help="FuseQL query string (no aggregations)")
    parser.add_argument("--minutes", type=int, default=60, help="Look-back window in minutes (default: 60)")
    parser.add_argument("--start", help="Start timestamp (RFC 3339), overrides --minutes")
    parser.add_argument("--end", help="End timestamp (RFC 3339), overrides --minutes")
    parser.add_argument("--max-rows", type=int, default=None, help="Stop after this many rows")
    parser.add_argument("--output", help="Write JSON Lines to this file (default: stdout)")
    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(tz=timezone.utc)
    end_ts = args.end or now.strftime("%Y-%m-%dT%H:%M:%SZ")
    start_ts = args.start or (now - timedelta(minutes=args.minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Host     : {args.host}", file=sys.stderr)
    print(f"Query    : {args.query}", file=sys.stderr)
    print(f"Range    : {start_ts} → {end_ts}", file=sys.stderr)
    if args.max_rows:
        print(f"Max rows : {args.max_rows}", file=sys.stderr)
    print(file=sys.stderr)

    if args.output:
        with open(args.output, "w") as f:
            fetch_all(args.host, args.token, args.query, start_ts, end_ts, args.max_rows, f)
        print(f"Output written to {args.output}", file=sys.stderr)
    else:
        fetch_all(args.host, args.token, args.query, start_ts, end_ts, args.max_rows, sys.stdout)


if __name__ == "__main__":
    main()
