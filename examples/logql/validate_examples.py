#!/usr/bin/env python3
"""
validate_examples.py — Run every documented LogQL example against a cluster.

Walks the per-operator directories (<category>/<operator>/README.md), extracts
the fenced ```logql example block, runs it through the Loki-compatible API,
and reports one of:

    PASS   query executed and returned data
    EMPTY  query executed but returned no data (may be fine for absent_over_time-style examples)
    FAIL   query was rejected or the request errored

Each README declares how to run its example with an HTML comment directly
above the example block:

    <!-- validation: kind=range minutes=10 -->
    ```logql
    {source="nginx"} |= "POST"
    ```

kind=range        log query via /loki/api/v1/query_range (default)
kind=range_metric metric query via /loki/api/v1/query_range
kind=instant      metric query via /loki/api/v1/query
minutes=N         look-back window (default 10)
expect=empty      an empty result counts as PASS (e.g. absent_over_time)

Queries run sequentially with a small delay between them to stay gentle on
shared clusters.

Usage:
    python3 validate_examples.py
    python3 validate_examples.py --only parse
    python3 validate_examples.py --only parse/json --show-output
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent

_MARKER_RE = re.compile(r"<!--\s*validation:\s*([^>]*?)\s*-->")
_BLOCK_RE = re.compile(r"```logql\n(.*?)\n```", re.DOTALL)


def parse_readme(path: Path):
    """Return (query, options) from the first validation marker + logql block."""
    text = path.read_text(encoding="utf-8")
    marker = _MARKER_RE.search(text)
    opts = {}
    if marker:
        for kv in marker.group(1).split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                opts[k] = v
        block = _BLOCK_RE.search(text, marker.end())
    else:
        block = _BLOCK_RE.search(text)
    if not block:
        return None, opts
    # Collapse the block to a single-line query (examples may wrap lines).
    query = " ".join(line.strip() for line in block.group(1).splitlines() if line.strip())
    return query, opts


def run_query(host, token, query, kind, minutes):
    end = int(time.time())
    if kind == "instant":
        url = f"https://{host}/loki/api/v1/query"
        params = {"query": query, "time": end}
    else:
        url = f"https://{host}/loki/api/v1/query_range"
        params = {"query": query, "start": end - minutes * 60, "end": end,
                  "step": 60, "limit": 10}
    try:
        resp = requests.get(url, params=params, timeout=90,
                            headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            return "FAIL", resp.text[:300], None
        body = resp.json()
    except Exception as exc:  # noqa: BLE001 — report any transport error
        return "FAIL", str(exc)[:300], None

    if body.get("status") != "success":
        return "FAIL", json.dumps(body)[:300], None

    data = body["data"]
    if not data["result"]:
        return "EMPTY", "", data
    return "PASS", "", data


def run_with_retry(host, token, query, kind, minutes):
    status, detail, data = run_query(host, token, query, kind, minutes)
    if status == "FAIL" and ("ServerNotResponding" in detail
                             or "timed out" in detail.lower()):
        time.sleep(45)
        status, detail, data = run_query(host, token, query, kind, minutes)
    return status, detail, data


def show(data, max_items=5):
    rtype = data["resultType"]
    if rtype == "streams":
        for stream in data["result"][:max_items]:
            for _, line in stream["values"][:2]:
                print(f"        {line[:150]}")
    elif rtype == "matrix":
        for series in data["result"][:max_items]:
            labels = json.dumps(series["metric"], sort_keys=True)
            print(f"        {labels[:100]}  last={series['values'][-1][1]}")
    elif rtype == "vector":
        for sample in data["result"][:max_items]:
            labels = json.dumps(sample["metric"], sort_keys=True)
            print(f"        {labels[:100]}  =>  {sample['value'][1]}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate documented LogQL examples.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--only", help="Limit to a category (parse) or operator (parse/json)")
    parser.add_argument("--show-output", action="store_true", help="Print a sample of each result")
    parser.add_argument("--delay", type=float, default=3.0,
                        help="Seconds to wait between queries (default: 3)")
    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        return 1

    readmes = sorted(HERE.glob("*/*/README.md"))
    if args.only:
        readmes = [p for p in readmes
                   if args.only in (p.parent.parent.name,
                                    f"{p.parent.parent.name}/{p.parent.name}")]
    if not readmes:
        print("No operator READMEs matched.", file=sys.stderr)
        return 1

    counts = {"PASS": 0, "EMPTY": 0, "FAIL": 0, "SKIP": 0}
    failures = []

    for path in readmes:
        name = f"{path.parent.parent.name}/{path.parent.name}"
        query, opts = parse_readme(path)
        if not query:
            print(f"SKIP  {name} (no ```logql block found)")
            counts["SKIP"] += 1
            continue

        kind = opts.get("kind", "range")
        minutes = int(opts.get("minutes", 10))
        status, detail, data = run_with_retry(args.host, args.token, query, kind, minutes)

        if status == "EMPTY" and opts.get("expect") == "empty":
            status = "PASS"

        counts[status] += 1
        print(f"{status:5s} {name}")
        if status == "FAIL":
            failures.append(name)
            print(f"      query: {query}")
            print(f"      error: {detail}")
        elif status == "EMPTY":
            print(f"      query: {query}")
        if args.show_output and data and data.get("result"):
            show(data)

        time.sleep(args.delay)

    print(f"\n{counts['PASS']} passed, {counts['EMPTY']} empty, "
          f"{counts['FAIL']} failed, {counts['SKIP']} skipped.")
    if failures:
        print("Failed:", ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
