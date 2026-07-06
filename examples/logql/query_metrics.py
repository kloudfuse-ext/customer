#!/usr/bin/env python3
"""
query_metrics.py — Run a LogQL metric query against Kloudfuse.

Uses the Loki-compatible endpoints:
  GET /loki/api/v1/query        (with --instant: one evaluation, vector result)
  GET /loki/api/v1/query_range  (default: evaluation per step, matrix result)

Usage:
    python3 query_metrics.py --instant --query 'sum by (level) (count_over_time({source="grafana"}[5m]))'
    python3 query_metrics.py --query 'rate({source="nginx"}[1m])' --minutes 30 --step 60
    python3 query_metrics.py --help
"""

import argparse
import json
import os
import sys
import time

import requests


def run_query(host: str, token: str, query: str, instant: bool,
              minutes: int, step: int) -> dict:
    end = int(time.time())
    if instant:
        url = f"https://{host}/loki/api/v1/query"
        params = {"query": query, "time": end}
    else:
        url = f"https://{host}/loki/api/v1/query_range"
        params = {"query": query, "start": end - minutes * 60, "end": end, "step": step}

    resp = requests.get(url, params=params, timeout=120,
                        headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    body = resp.json()
    if body.get("status") != "success":
        print(f"Query failed: {json.dumps(body)[:400]}", file=sys.stderr)
        sys.exit(1)
    return body["data"]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a LogQL metric query against Kloudfuse.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--query", required=True, help="LogQL metric query")
    parser.add_argument("--instant", action="store_true",
                        help="Evaluate once at now (vector result) instead of over a range")
    parser.add_argument("--minutes", type=int, default=30,
                        help="Range query look-back window in minutes (default: 30)")
    parser.add_argument("--step", type=int, default=60,
                        help="Range query resolution in seconds (default: 60)")
    parser.add_argument("--json", action="store_true", help="Print the raw JSON response data")
    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        sys.exit(1)

    data = run_query(args.host, args.token, args.query, args.instant,
                     args.minutes, args.step)

    if args.json:
        json.dump(data, sys.stdout, indent=2)
        print()
        return

    result = data["result"]
    if not result:
        print("(empty result)")
        return

    if data["resultType"] == "vector":
        for sample in result:
            labels = json.dumps(sample["metric"], sort_keys=True)
            print(f"{labels}  =>  {sample['value'][1]}")
    elif data["resultType"] == "matrix":
        for series in result:
            labels = json.dumps(series["metric"], sort_keys=True)
            first_ts, first_v = series["values"][0]
            last_ts, last_v = series["values"][-1]
            print(f"{labels}  ({len(series['values'])} points, "
                  f"first={first_v}, last={last_v})")
    else:
        print(f"Unexpected resultType={data['resultType']} — "
              f"use fetch_logs.py for log queries.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
