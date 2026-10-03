#!/usr/bin/env python3
"""
grok_tester.py — Test a Kloudfuse logs-parser grok pattern against a sample line.

Kloudfuse grok patterns use the same syntax as the Logstash grok filter plugin
(see the Kloudfuse docs, Data Management -> Log Parsing -> Configuration,
"Grok patterns"). This wraps the `pygrok` library, which implements that same
Oniguruma-based pattern set, so a pattern that passes here is syntactically
the same pattern Kloudfuse will load — it does not confirm Kloudfuse's exact
field-typing or facet-naming behavior, only that the pattern compiles and
extracts the fields you expect from a sample line.

Requires: pip install pygrok

Usage:
    python3 grok_tester.py --pattern '%{IP:client_ip} - %{USER:user}' \
        --line '192.168.1.1 - john'
    python3 grok_tester.py --pattern '%{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} %{GREEDYDATA:msg}' \
        --line '2024-01-16T10:30:00Z ERROR Connection failed' \
        --expect '{"ts": "2024-01-16T10:30:00Z", "level": "ERROR", "msg": "Connection failed"}'
"""

import argparse
import json
import sys

try:
    from pygrok import Grok
except ImportError:
    print("Error: pygrok is required — pip install pygrok", file=sys.stderr)
    sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pattern", action="append", required=True,
                        help="Grok pattern; repeat --pattern to combine several (as Kloudfuse's "
                             "`patterns` list does)")
    parser.add_argument("--line", required=True, help="Sample log line to match")
    parser.add_argument("--expect", help="JSON object of expected fields; exits non-zero on mismatch")
    args = parser.parse_args()

    combined = "".join(args.pattern)
    grok = Grok(combined)
    fields = grok.match(args.line)

    if fields is None:
        print(f"FAIL: pattern did not match the line.\n  pattern: {combined}\n  line:    {args.line}",
              file=sys.stderr)
        sys.exit(1)

    print(json.dumps(fields, indent=2))

    if args.expect:
        expected = json.loads(args.expect)
        if fields != expected:
            print(f"\nFAIL: expected {expected}, got {fields}", file=sys.stderr)
            sys.exit(1)
        print("\nPASS", file=sys.stderr)


if __name__ == "__main__":
    main()
