#!/usr/bin/env python3
"""
query_log_metrics.py — Run a FuseQL aggregation query against Kloudfuse logs.

Uses the getLogMetricsResultWithKfuseQl GraphQL query, which supports the full
FuseQL operator set including timeslice, count, sum, avg, percentiles, and group-by.

Usage:
    python3 query_log_metrics.py --query '* | timeslice 5m | count by (_timeslice)'
    python3 query_log_metrics.py --query 'level="error" | count by (source)' --minutes 30
    python3 query_log_metrics.py --help
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

GRAPHQL_QUERY = """
{
  getLogMetricsResultWithKfuseQl(
    query: %(query)s
    startTs: %(start_ts)s
    endTs: %(end_ts)s
  ) {
    ColumnHeaders
    AggrValues
    GroupKeys
    TimeKey
    TableResult
    UrlValues
  }
}
"""


def run_query(host: str, token: str, fuseql: str, start_ts: str, end_ts: str) -> dict:
    payload = {
        "query": GRAPHQL_QUERY % {
            "query": json.dumps(fuseql),
            "start_ts": json.dumps(start_ts),
            "end_ts": json.dumps(end_ts),
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

    return body["data"]["getLogMetricsResultWithKfuseQl"]


def format_table(result: dict) -> None:
    headers = result.get("ColumnHeaders") or []
    rows = result.get("TableResult") or []

    if not headers:
        print("(no results)")
        return

    # Convert epoch ms timestamps to human-readable
    time_key = result.get("TimeKey")
    time_col_idx = headers.index(time_key) if time_key and time_key in headers else None

    col_widths = [len(h) for h in headers]
    formatted_rows = []
    for row in rows:
        fmt = []
        for i, val in enumerate(row):
            if i == time_col_idx and isinstance(val, (int, float)):
                val = datetime.fromtimestamp(val / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
            fmt.append(str(val))
            col_widths[i] = max(col_widths[i], len(str(val)))
        formatted_rows.append(fmt)

    sep = "  ".join("-" * w for w in col_widths)
    header_line = "  ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    print(header_line)
    print(sep)
    for row in formatted_rows:
        print("  ".join(v.ljust(col_widths[i]) for i, v in enumerate(row)))

    print(f"\n{len(rows)} row(s)")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a FuseQL aggregation query.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--query", required=True, help="FuseQL query string")
    parser.add_argument("--minutes", type=int, default=60, help="Look-back window in minutes (default: 60)")
    parser.add_argument("--start", help="Start timestamp (RFC 3339), overrides --minutes")
    parser.add_argument("--end", help="End timestamp (RFC 3339), overrides --minutes")
    parser.add_argument("--json", dest="output_json", action="store_true", help="Print raw JSON result")
    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(tz=timezone.utc)
    end_ts = args.end or now.strftime("%Y-%m-%dT%H:%M:%SZ")
    start_ts = args.start or (now - timedelta(minutes=args.minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")

    print(f"Host   : {args.host}", file=sys.stderr)
    print(f"Query  : {args.query}", file=sys.stderr)
    print(f"Range  : {start_ts} → {end_ts}", file=sys.stderr)
    print(file=sys.stderr)

    result = run_query(args.host, args.token, args.query, start_ts, end_ts)

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        format_table(result)


if __name__ == "__main__":
    main()
