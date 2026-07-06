#!/usr/bin/env python3
"""
validate_examples.py — Run every documented TraceQL example against a cluster.

Walks the per-operator directories (<category>/<operator>/README.md), extracts
the fenced ```traceql example block, and runs it through the Tempo-compatible
search API served by the Grafana datasource proxy:

    GET /grafana/api/datasources/proxy/uid/<DS_UID>/api/search?q=...

Reports PASS (traces returned), EMPTY (ran, no traces), FAIL (rejected).
A README can mark an intentionally empty example with expect=empty in its
validation marker.

Usage:
    export KLOUDFUSE_HOST=<hostname> KLOUDFUSE_TOKEN=glsa_...
    python3 validate_examples.py
    python3 validate_examples.py --only aggregation
    python3 validate_examples.py --only aggregation/count
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
DEFAULT_DS_UID = "PF79758345A66D57F"  # KfuseTraceDatasource

_MARKER_RE = re.compile(r"<!--\s*validation:\s*([^>]*?)\s*-->")
_BLOCK_RE = re.compile(r"```traceql\n(.*?)\n```", re.DOTALL)


def parse_readme(path):
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
    query = " ".join(l.strip() for l in block.group(1).splitlines() if l.strip())
    return query, opts


def run_query(host, token, ds_uid, query, minutes):
    end = int(time.time())
    url = f"https://{host}/grafana/api/datasources/proxy/uid/{ds_uid}/api/search"
    try:
        resp = requests.get(url, params={"q": query, "start": end - minutes * 60,
                                         "end": end, "limit": 5},
                            timeout=90, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            return "FAIL", resp.text[:300]
        body = resp.json()
    except Exception as exc:  # noqa: BLE001
        return "FAIL", str(exc)[:300]
    if "error" in body:
        return "FAIL", json.dumps(body)[:300]
    return ("PASS", "") if body.get("traces") else ("EMPTY", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    ap.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    ap.add_argument("--ds-uid", default=os.environ.get("KLOUDFUSE_TRACE_DS_UID", DEFAULT_DS_UID))
    ap.add_argument("--only")
    ap.add_argument("--delay", type=float, default=2.0)
    args = ap.parse_args()
    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        return 1

    readmes = sorted(HERE.glob("*/*/README.md"))
    if args.only:
        readmes = [p for p in readmes
                   if args.only in (p.parent.parent.name,
                                    f"{p.parent.parent.name}/{p.parent.name}")]
    counts = {"PASS": 0, "EMPTY": 0, "FAIL": 0, "SKIP": 0}
    failures = []
    for path in readmes:
        name = f"{path.parent.parent.name}/{path.parent.name}"
        query, opts = parse_readme(path)
        if not query:
            counts["SKIP"] += 1
            print(f"SKIP  {name}")
            continue
        status, detail = run_query(args.host, args.token, args.ds_uid, query,
                                   int(opts.get("minutes", 15)))
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
        time.sleep(args.delay)
    print(f"\n{counts['PASS']} passed, {counts['EMPTY']} empty, "
          f"{counts['FAIL']} failed, {counts['SKIP']} skipped.")
    if failures:
        print("Failed:", ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
