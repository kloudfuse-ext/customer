#!/usr/bin/env python3
"""
fetch_logs.py — Fetch raw log lines from Kloudfuse with a LogQL log query.

Uses the Loki-compatible endpoint GET /loki/api/v1/query_range with a log
query (stream selector + optional pipeline, no metric wrapper).

Usage:
    python3 fetch_logs.py --query '{source="nginx"} |= "POST"'
    python3 fetch_logs.py --query '{source="grafana"} | logfmt | duration > 100ms' --minutes 30
    python3 fetch_logs.py --query '{source="nginx"}' --limit 50 --output lines.jsonl
    python3 fetch_logs.py --help
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests


def fetch(host: str, token: str, query: str, start: datetime, end: datetime,
          limit: int, direction: str) -> dict:
    resp = requests.get(
        f"https://{host}/loki/api/v1/query_range",
        params={
            "query": query,
            "start": int(start.timestamp()),
            "end": int(end.timestamp()),
            "limit": limit,
            "direction": direction,
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != "success":
        print(f"Query failed: {json.dumps(body)[:400]}", file=sys.stderr)
        sys.exit(1)
    return body["data"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch raw log lines from Kloudfuse with LogQL.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--query", required=True, help="LogQL log query (no metric wrapper)")
    parser.add_argument("--minutes", type=int, default=10, help="Look-back window in minutes (default: 10)")
    parser.add_argument("--start", help="Start timestamp (RFC 3339), overrides --minutes")
    parser.add_argument("--end", help="End timestamp (RFC 3339), overrides --minutes")
    parser.add_argument("--limit", type=int, default=100, help="Maximum lines to return (default: 100)")
    parser.add_argument("--direction", choices=["backward", "forward"], default="backward",
                        help="Return newest lines first (backward, default) or oldest first")
    parser.add_argument("--output", help="Write JSON Lines to this file (default: stdout, lines only)")
    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        sys.exit(1)

    now = datetime.now(tz=timezone.utc)
    end = datetime.fromisoformat(args.end.replace("Z", "+00:00")) if args.end else now
    start = (datetime.fromisoformat(args.start.replace("Z", "+00:00"))
             if args.start else now - timedelta(minutes=args.minutes))

    print(f"Host  : {args.host}", file=sys.stderr)
    print(f"Query : {args.query}", file=sys.stderr)
    print(f"Range : {start.isoformat()} → {end.isoformat()}", file=sys.stderr)
    print(file=sys.stderr)

    data = fetch(args.host, args.token, args.query, start, end, args.limit, args.direction)

    if data["resultType"] != "streams":
        print(f"Expected a log query but got resultType={data['resultType']} — "
              f"use query_metrics.py for metric queries.", file=sys.stderr)
        sys.exit(1)

    out = open(args.output, "w") if args.output else sys.stdout
    total = 0
    for stream in data["result"]:
        for ts_ns, line in stream["values"]:
            ts = datetime.fromtimestamp(int(ts_ns) / 1e9, tz=timezone.utc)
            if args.output:
                out.write(json.dumps({
                    "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
                    "line": line,
                    "stream": stream["stream"],
                }) + "\n")
            else:
                out.write(f"{ts.strftime('%H:%M:%S')}  {line}\n")
            total += 1

    if args.output:
        out.close()
        print(f"{total} line(s) written to {args.output}", file=sys.stderr)
    else:
        print(f"\n{total} line(s).", file=sys.stderr)


if __name__ == "__main__":
    main()
