#!/usr/bin/env python3
"""Check that Blackbox Exporter probe results from this example arrived in Kloudfuse.

For each collection method, queries probe_success by job and compares every
expected target's value. Exits non-zero if any check fails.

    export KLOUDFUSE_HOST=<kloudfuse-hostname>
    export KLOUDFUSE_TOKEN=glsa_...
    python3 validate.py [--only prometheus|otel|operator]
"""
import argparse
import os
import sys

import requests


def expected(host):
    """Expected {(job, instance): probe_success} per collection method."""
    return {
        "prometheus": {
            ("blackbox-http", "https://example.com"): 1,
            ("blackbox-http", "https://httpbin.org/status/200"): 1,
            ("blackbox-http", "https://does-not-exist.invalid"): 0,
            ("blackbox-tcp", f"{host}:443"): 1,
            ("blackbox-icmp", "8.8.8.8"): 1,
            ("blackbox-dns", "8.8.8.8:53"): 1,
        },
        "otel": {
            ("otel-blackbox-http", "https://example.com"): 1,
            ("otel-blackbox-http", "https://httpbin.org/status/200"): 1,
        },
        "operator": {
            ("blackbox-prometheus-blackbox-exporter", "https://example.com"): 1,
            ("blackbox-prometheus-blackbox-exporter", "https://httpbin.org/status/200"): 1,
            ("blackbox-prometheus-blackbox-exporter", f"{host}:443"): 1,
            ("probe/monitoring/public-endpoints", "https://example.com"): 1,
            ("probe/monitoring/public-endpoints", "https://httpbin.org/status/200"): 1,
        },
    }


def query(host, token, expr):
    resp = requests.get(f"https://{host}/api/v1/query", params={"query": expr}, timeout=60,
                        headers={"Authorization": f"Bearer {token}"})
    resp.raise_for_status()
    return resp.json()["data"]["result"]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default=os.environ.get("KLOUDFUSE_HOST", ""))
    parser.add_argument("--token", default=os.environ.get("KLOUDFUSE_TOKEN", ""))
    parser.add_argument("--only", choices=["prometheus", "otel", "operator"])
    args = parser.parse_args()
    if not args.host or not args.token:
        print("Error: set KLOUDFUSE_HOST and KLOUDFUSE_TOKEN (or pass --host/--token)", file=sys.stderr)
        return 2

    failures = 0
    for method, checks in expected(args.host).items():
        if args.only and method != args.only:
            continue
        print(f"== {method}")
        jobs = "|".join(sorted({job for job, _ in checks}))
        # max_over_time tolerates a scrape that has not landed yet at query time.
        rows = query(args.host, args.token, f'max_over_time(probe_success{{job=~"{jobs}"}}[5m])')
        actual = {(r["metric"].get("job"), r["metric"].get("instance")): int(float(r["value"][1]))
                  for r in rows}
        for (job, instance), want in checks.items():
            got = actual.get((job, instance))
            if got == want:
                status = "PASS"
            else:
                status = "FAIL"
                failures += 1
            print(f"  {status}  {job:40} {instance:36} want={want} got={got}")

    print(f"\n{'OK' if not failures else f'{failures} check(s) failed'}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
