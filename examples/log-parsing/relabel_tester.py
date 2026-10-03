#!/usr/bin/env python3
"""
relabel_tester.py — Test a Kloudfuse logs-parser relabel/transform rule against sample
facets and labels.

Implements the action set documented in the Kloudfuse docs (Data Management ->
Log Parsing -> Configuration, "Relabel" / "Transform") — `replace`, `drop`,
`keep`, `lowercase`, `uppercase`, `label_map`, `label_keep`, `label_drop`, and
`facet_to_label_map`. `relabel` and `transform` are the same engine; this
tester covers both.

This simulates the action logic described in the docs to validate a rule
before pasting it into Helm values — it is not the production implementation,
so confirm exact edge-case behavior (prefix precedence, escaping) against a
running cluster.

Usage:
    python3 relabel_tester.py \
        --args '{"action": "replace", "regex": ".*", "replacement": "production", "targetLabel": "env"}' \
        --facets '{}' --labels '{}'

    python3 relabel_tester.py \
        --args '{"action": "drop", "sourceLabels": "@path", "regex": "/healthz"}' \
        --facets '{"path": "/healthz"}' --labels '{}'
"""

import argparse
import json
import re
import sys


class DroppedError(Exception):
    """Raised when `drop` or `keep` discards the log line."""


def resolve_source(name: str, facets: dict, labels: dict) -> str:
    if name.startswith("@"):
        return facets.get(name[1:], "")
    if name.startswith("#"):
        return labels.get(name[1:], "")
    return labels.get(name, "")


def apply_action(args: dict, facets: dict, labels: dict) -> tuple[dict, dict]:
    facets, labels = dict(facets), dict(labels)
    action = args["action"]
    source_names = [s.strip() for s in args.get("sourceLabels", "").split(",") if s.strip()]
    separator = args.get("separator", ";")
    source_value = separator.join(resolve_source(n, facets, labels) for n in source_names)
    regex = args.get("regex", "")
    target = args.get("targetLabel", "")

    def write(name: str, value: str):
        if name.startswith("@"):
            facets[name[1:]] = value
        else:
            labels[name] = value

    if action == "replace":
        if re.search(regex, source_value):
            write(target, args.get("replacement", ""))
    elif action == "drop":
        if re.search(regex, source_value):
            raise DroppedError(f"log line dropped: {source_value!r} matched {regex!r}")
    elif action == "keep":
        if not re.search(regex, source_value):
            raise DroppedError(f"log line dropped: {source_value!r} did not match {regex!r}")
    elif action == "lowercase":
        write(target, source_value.lower())
    elif action == "uppercase":
        write(target, source_value.upper())
    elif action == "label_map":
        replacement = args.get("replacement", "")
        labels = {re.sub(regex, replacement, k) if re.search(regex, k) else k: v for k, v in labels.items()}
    elif action == "label_keep":
        labels = {k: v for k, v in labels.items() if re.search(regex, k)}
    elif action == "label_drop":
        labels = {k: v for k, v in labels.items() if not re.search(regex, k)}
    elif action == "facet_to_label_map":
        src = source_names[0]
        value = resolve_source(src, facets, labels)
        if regex:
            value = re.sub(regex, args.get("replacement", ""), value)
        labels[target] = value
    else:
        raise ValueError(f"Unknown action: {action}")

    return facets, labels


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--args", required=True, help="JSON object of the rule's `args`")
    parser.add_argument("--facets", default="{}", help="JSON object of facets before this rule runs")
    parser.add_argument("--labels", default="{}", help="JSON object of labels before this rule runs")
    parser.add_argument("--expect", help="JSON {\"facets\": {...}, \"labels\": {...}}; exits non-zero on mismatch")
    args = parser.parse_args()

    rule_args = json.loads(args.args)
    facets = json.loads(args.facets)
    labels = json.loads(args.labels)

    try:
        out_facets, out_labels = apply_action(rule_args, facets, labels)
    except DroppedError as e:
        print(json.dumps({"dropped": True, "reason": str(e)}, indent=2))
        if args.expect:
            expected = json.loads(args.expect)
            ok = expected.get("dropped") is True
            print("\nPASS" if ok else f"\nFAIL: expected {expected}", file=sys.stderr)
            sys.exit(0 if ok else 1)
        return

    result = {"facets": out_facets, "labels": out_labels}
    print(json.dumps(result, indent=2))

    if args.expect:
        expected = json.loads(args.expect)
        if result != expected:
            print(f"\nFAIL: expected {expected}, got {result}", file=sys.stderr)
            sys.exit(1)
        print("\nPASS", file=sys.stderr)


if __name__ == "__main__":
    main()
