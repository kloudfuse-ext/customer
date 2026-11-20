#!/usr/bin/env python3
"""
check_fingerprint.py — Validate the fingerprint examples in README.md against a live cluster.

Runs each documented query and checks the results against each other, so it
works on any cluster with logs from the chosen source:

  * raw log rows return __kf_fp and __kf_fp_hash (not fpString / fpHash)
  * count by (__kf_fp_hash) and count by (fp_hash) return the same groups
  * __kf_fp_hash="A"           count == A's group count
  * __kf_fp_hash!="A"          count == total - A
  * __kf_fp_hash in ("A","B")  count == A + B
  * fp_hash and fingerprint    behave like __kf_fp_hash
  * __kf_fp                   cannot be filtered (matches nothing)
  * regex on the hash          is rejected

Usage:
    export KLOUDFUSE_HOST=<kloudfuse-hostname>
    export KLOUDFUSE_TOKEN=<service-account-token>
    python3 check_fingerprint.py --source grafana --minutes 15
"""

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

METRICS_QUERY = """
{
  getLogMetricsResultWithKfuseQl(query: %(query)s, startTs: %(start)s, endTs: %(end)s) {
    ColumnHeaders
    TableResult
  }
}
"""

STREAM_QUERY = """
subscription {
  getLogsWithFuseQlStream(query: %(query)s, startTs: %(start)s, endTs: %(end)s, cursor: null) {
    ColumnHeaders
    TableResult
  }
}
"""


class Client:
    def __init__(self, url, token, start, end):
        self.url = url
        self.headers = {"Content-Type": "application/json"}
        if token:
            self.headers["Authorization"] = f"Bearer {token}"
        self.start = json.dumps(start.strftime("%Y-%m-%dT%H:%M:%SZ"))
        self.end = json.dumps(end.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def _post(self, template, fuseql):
        gql = template % {"query": json.dumps(fuseql), "start": self.start, "end": self.end}
        resp = requests.post(self.url, headers=self.headers, json={"query": gql}, timeout=180)
        resp.raise_for_status()
        body = resp.json()
        if body.get("errors"):
            raise RuntimeError(body["errors"][0].get("message", "unknown error"))
        return next(iter(body["data"].values()))

    def metrics(self, fuseql):
        return self._post(METRICS_QUERY, fuseql)

    def stream(self, fuseql):
        return self._post(STREAM_QUERY, fuseql)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", ""))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--url", help="Full /query URL; overrides --host (e.g. http://localhost:8080/query)")
    parser.add_argument("--source", default="grafana", help="Log source to test against (default: grafana)")
    parser.add_argument("--minutes", type=int, default=15, help="Time window in minutes (default: 15)")
    args = parser.parse_args()

    url = args.url or (f"https://{args.host}/query" if args.host else None)
    if not url:
        sys.exit("Set KLOUDFUSE_HOST (or pass --host or --url).")

    # End the window a couple of minutes ago so counts do not move between queries.
    end = datetime.now(timezone.utc) - timedelta(minutes=2)
    client = Client(url, args.token, end - timedelta(minutes=args.minutes), end)
    src = f'source="{args.source}"'

    passed = failed = 0

    def check(name, ok, detail=""):
        nonlocal passed, failed
        if ok:
            passed += 1
            print(f"  PASS  {name}")
        else:
            failed += 1
            print(f"  FAIL  {name}  {detail}")

    # Raw rows carry the new column names.
    headers = client.stream(f"{src} | limit 1")["ColumnHeaders"]
    check("raw rows return __kf_fp and __kf_fp_hash",
          "__kf_fp" in headers and "__kf_fp_hash" in headers, headers)
    check("raw rows no longer return fpString / fpHash",
          "fpString" not in headers and "fpHash" not in headers, headers)

    # Group by fingerprint hash; pick the two largest groups as A and B.
    groups = client.metrics(f"{src} | count by (__kf_fp_hash) | sort by _count desc")["TableResult"]
    if len(groups) < 2:
        sys.exit(f"Need at least two fingerprints for {src}; widen --minutes or change --source.")
    (count_a, hash_a), (count_b, hash_b) = groups[0], groups[1]
    total = client.metrics(f"{src} | count")["TableResult"][0][0]
    print(f"  info  {src}: {total} logs, {len(groups)} fingerprints; "
          f"A={hash_a} ({count_a}), B={hash_b} ({count_b})")

    legacy = client.metrics(f"{src} | count by (fp_hash) | sort by _count desc")["TableResult"]
    # Compare as sets: groups with equal counts can come back in any order.
    check("count by (fp_hash) matches count by (__kf_fp_hash)",
          sorted(map(tuple, legacy)) == sorted(map(tuple, groups)))

    unique = client.metrics(f"{src} | count_unique(__kf_fp_hash)")["TableResult"][0][0]
    check("count_unique(__kf_fp_hash) == number of groups", int(unique) == len(groups), unique)

    def count(where):
        return client.metrics(f"{src} and {where} | count")["TableResult"][0][0]

    check('__kf_fp_hash="A"', count(f'__kf_fp_hash="{hash_a}"') == count_a)
    check('fp_hash="A"', count(f'fp_hash="{hash_a}"') == count_a)
    check('fingerprint="A"', count(f'fingerprint="{hash_a}"') == count_a)
    check('__kf_fp_hash!="A"', count(f'__kf_fp_hash!="{hash_a}"') == total - count_a)
    check('__kf_fp_hash in ("A","B")', count(f'__kf_fp_hash in ("{hash_a}","{hash_b}")') == count_a + count_b)

    # The fingerprint template itself, for the largest group.
    row = client.stream(f'{src} and __kf_fp_hash="{hash_a}" | limit 1')
    template = row["TableResult"][0][row["ColumnHeaders"].index("__kf_fp")]
    print(f"  info  fingerprint A: {template[:100]}")
    check("__kf_fp is not filterable (matches nothing)",
          count(f"__kf_fp={json.dumps(template)}") == 0)

    try:
        client.metrics(f'{src} and __kf_fp_hash=~"{hash_a[:6]}.*" | count')
        check("regex on __kf_fp_hash is rejected", False, "query succeeded")
    except RuntimeError as err:
        check("regex on __kf_fp_hash is rejected", "unsupported operator" in str(err), err)

    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
