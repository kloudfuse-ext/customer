#!/usr/bin/env python3
"""
validate_examples.py — Run every documented audit/performance-log example.

Extracts each fenced ```fuseql block from README.md (paired with a preceding
`<!-- validation: ... -->` marker) and runs it against a live Kloudfuse
cluster, reporting one of:

    PASS   query executed and returned data
    EMPTY  query executed but returned no rows in the window
    FAIL   query was rejected or the request errored

Validation markers:

    kind=metric   run via getLogMetricsResultWithKfuseQl (aggregations)  [default]
    kind=raw      run via getLogsWithFuseQlStream (filter-only queries)
    minutes=N     look-back window (default 1440)
    expect=empty  an empty result counts as PASS (illustrative placeholders)

Usage:
    export KLOUDFUSE_HOST=observe.kloudfuse.io
    export KLOUDFUSE_TOKEN=glsa_...
    python3 validate_examples.py
    python3 validate_examples.py --show-output
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
README = HERE / "README.md"

_MARKER_RE = re.compile(r"<!--\s*validation:\s*([^>]*?)\s*-->\s*```fuseql\n(.*?)\n```",
                        re.DOTALL)

_METRIC_GQL = """
query {
  getLogMetricsResultWithKfuseQl(query: %(q)s, startTs: %(s)s, endTs: %(e)s) {
    ColumnHeaders TableResult
  }
}
"""

_RAW_GQL = """
subscription {
  getLogsWithFuseQlStream(query: %(q)s, startTs: %(s)s, endTs: %(e)s, cursor: null) {
    ColumnHeaders TableResult Cursor
  }
}
"""


def parse_examples(text):
    """Yield (title, query, opts) for each validated example block."""
    for m in _MARKER_RE.finditer(text):
        opts = dict(kv.split("=", 1) for kv in m.group(1).split() if "=" in kv)
        query = " ".join(l.strip() for l in m.group(2).splitlines() if l.strip())
        # Nearest preceding "### " heading is the title.
        heading = None
        for line in text[:m.start()].splitlines()[::-1]:
            if line.startswith("### "):
                heading = line[4:].strip()
                break
        yield heading or query[:50], query, opts


def run(host, token, query, kind, minutes):
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    tmpl = _RAW_GQL if kind == "raw" else _METRIC_GQL
    body = tmpl % {
        "q": json.dumps(query),
        "s": json.dumps(start.strftime("%Y-%m-%dT%H:%M:%SZ")),
        "e": json.dumps(end.strftime("%Y-%m-%dT%H:%M:%SZ")),
    }
    try:
        resp = requests.post(
            f"https://{host}/query",
            headers={"Authorization": f"Bearer {token}",
                     "Content-Type": "application/json"},
            json={"query": body}, timeout=120)
        payload = resp.json()
    except Exception as exc:  # noqa: BLE001 — report any transport error
        return "FAIL", str(exc)[:300], None

    if "errors" in payload:
        return "FAIL", "; ".join(e["message"] for e in payload["errors"])[:300], None

    key = "getLogsWithFuseQlStream" if kind == "raw" else "getLogMetricsResultWithKfuseQl"
    data = (payload.get("data") or {}).get(key)
    if data is None:
        return "FAIL", json.dumps(payload)[:300], None

    tr = data.get("TableResult")
    rows = 0
    if tr:
        try:
            rows = len(json.loads(tr)) if isinstance(tr, str) else len(tr)
        except Exception:
            rows = 1
    return ("PASS" if rows else "EMPTY"), rows, data


def main():
    parser = argparse.ArgumentParser(description="Validate audit/perf log examples.")
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", "<kloudfuse-hostname>"))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--minutes", type=int, default=1440, help="Default look-back (min)")
    parser.add_argument("--show-output", action="store_true")
    parser.add_argument("--delay", type=float, default=2.0)
    args = parser.parse_args()

    if not args.token:
        print("Error: provide --token or set KLOUDFUSE_TOKEN", file=sys.stderr)
        return 1

    counts = {"PASS": 0, "EMPTY": 0, "FAIL": 0}
    failures = []

    for title, query, opts in parse_examples(README.read_text(encoding="utf-8")):
        kind = opts.get("kind", "metric")
        minutes = int(opts.get("minutes", args.minutes))
        status, detail, data = run(args.host, args.token, query, kind, minutes)
        if status == "EMPTY" and opts.get("expect") == "empty":
            status = "PASS"
        counts[status] += 1
        print(f"{status:5s} {title}  (rows={detail if status!='FAIL' else '-'})")
        if status == "FAIL":
            failures.append(title)
            print(f"      query: {query}")
            print(f"      error: {detail}")
        if args.show_output and data and data.get("TableResult"):
            print(f"      {str(data['TableResult'])[:200]}")
        time.sleep(args.delay)

    print(f"\n{counts['PASS']} passed, {counts['EMPTY']} empty, {counts['FAIL']} failed.")
    if failures:
        print("Failed:", ", ".join(failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
