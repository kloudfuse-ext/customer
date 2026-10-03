#!/usr/bin/env python3
"""
dissect_tester.py — Test a Kloudfuse logs-parser dissect tokenizer against a sample line.

Reimplements the subset of dissect syntax documented in the Kloudfuse docs
(Data Management -> Log Parsing -> Configuration, "Dissect patterns"):

    %{fieldname}   capture the text up to the next literal delimiter
    %{?fieldname}  match without capturing
    %{+fieldname}  append this capture to a field captured earlier in the
                   pattern, joined with a space (Logstash dissect's default
                   append_separator)

A trailing field with no literal delimiter after it (the pattern's last
`%{field}`, nothing following) stops at the next whitespace rather than
consuming the rest of the line — confirmed against a running logs-parser's
`/pipeline/test-function` API, which is *not* how the generic Logstash
dissect filter this syntax is modeled on behaves, so don't assume the two are
identical beyond what's documented here.

This is a lightweight, local approximation of the engine for validating a
pattern's *shape* before you paste it into Helm values and deploy — it does
not implement the `%{&ref}` key/value-reference modifier or `[bracket][nested]`
field names. For those, or to confirm exact edge-case behavior, use the
dissect debugger linked from the docs (https://dissect-tester.jorgelbg.me/)
or test against a running cluster.

Usage:
    python3 dissect_tester.py --tokenizer '%{a} %{b}' --line 'foo bar'
    python3 dissect_tester.py --tokenizer '%{a} %{b}' --line 'foo bar' \
        --expect '{"a": "foo", "b": "bar"}'
"""

import argparse
import json
import re
import sys


class DissectError(Exception):
    pass


def compile_tokenizer(tokenizer: str):
    """Return (regex, fields) where fields is [(group_name, real_name, skip, append), ...]."""
    parts = re.split(r"(%\{[^}]*\})", tokenizer)
    regex_parts = []
    fields = []
    # Find indices of capturing (non-skip) placeholders to know which is last.
    placeholder_idxs = [i for i, p in enumerate(parts) if p.startswith("%{") and p.endswith("}")]

    for i, part in enumerate(parts):
        if not part:
            continue
        if part.startswith("%{") and part.endswith("}"):
            inner = part[2:-1]
            skip = inner.startswith("?")
            append = inner.startswith("+")
            if skip or append:
                name = inner[1:]
            else:
                name = inner
            if "&" in part or "[" in name:
                raise DissectError(
                    "%{&ref} and [bracket][nested] field names are not supported by this "
                    "lightweight tester — use the dissect debugger linked from the docs."
                )
            group_name = f"g{len(fields)}"
            is_last_capturing = i == placeholder_idxs[-1]
            # A field is only "trailing" (no literal delimiter after it anywhere in the
            # pattern) if nothing but empty splits follows it — confirmed against a running
            # cluster to stop at the next whitespace, not consume the rest of the line.
            is_trailing_field = is_last_capturing and all(p == "" for p in parts[i + 1:])
            if skip:
                body = r"[^\s]*" if is_trailing_field else (r".*" if is_last_capturing else r".*?")
                regex_parts.append(f"(?:{body})")
            elif is_trailing_field:
                regex_parts.append(f"(?P<{group_name}>[^\\s]*)")
            else:
                regex_parts.append(f"(?P<{group_name}>.*)" if is_last_capturing else f"(?P<{group_name}>.*?)")
            fields.append((group_name, name, skip, append))
        else:
            regex_parts.append(re.escape(part))

    # Anchored at the start only — like the real engine, trailing content beyond what the
    # pattern describes is ignored rather than required to match to end-of-line.
    pattern = "^" + "".join(regex_parts)
    return re.compile(pattern, re.DOTALL), fields


def dissect(tokenizer: str, line: str) -> dict:
    regex, fields = compile_tokenizer(tokenizer)
    match = regex.match(line)
    if not match:
        raise DissectError(f"Tokenizer did not match the line.\n  tokenizer: {tokenizer}\n  line:      {line}")

    result = {}
    for group_name, name, skip, append in fields:
        if skip:
            continue
        value = match.group(group_name)
        if append and name in result:
            result[name] = f"{result[name]} {value}"
        else:
            result[name] = value
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tokenizer", required=True, help="Dissect tokenizer, e.g. '%%{a} %%{b}'")
    parser.add_argument("--line", required=True, help="Sample log line to tokenize")
    parser.add_argument("--expect", help="JSON object of expected facets; exits non-zero on mismatch")
    args = parser.parse_args()

    try:
        facets = dissect(args.tokenizer, args.line)
    except DissectError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(facets, indent=2))

    if args.expect:
        expected = json.loads(args.expect)
        if facets != expected:
            print(f"\nFAIL: expected {expected}, got {facets}", file=sys.stderr)
            sys.exit(1)
        print("\nPASS", file=sys.stderr)


if __name__ == "__main__":
    main()
