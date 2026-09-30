#!/usr/bin/env python3
"""
validate_examples.py — Run every documented logs-parser-config example.

Walks the per-function directories (<category>/<function>/README.md), extracts
each example's pipeline YAML and sample payload, runs them through the
logs-parser Pipeline API's POST /pipeline/test-function, and reports one of:

    PASS    request succeeded and the declared expectation was met
    FAIL    request was rejected, errored, or the expectation was not met
    MANUAL  request succeeded (or was dropped); no automated expectation
            declared — inspect the printed response yourself

Each README declares how to validate its example with an HTML comment
directly above the pipeline YAML block:

    <!-- validation: expect=facet:status=200 -->
    ```yaml
    - parser:
        dissect:
          args:
            - tokenizer: '...'
    ```
    ```json
    {"message": "...", "ddsource": "myapp"}
    ```

expect=facet:<name>=<value>    result.facets[<name>] == <value>
expect=tag:<name>=<value>      result.tags[<name>] == <value>
expect=level:<value>           result.logLevel == <value>
expect=fingerprint:<substring> <substring> in result.fingerprintString
expect=dropped                 the event was dropped — success=false with
                                error "Event was dropped by the pipeline"
                                (verified response shape for drop/keep/
                                dropLogLine; NOT documented in PipelineApi.md)
expect=manual                  no automated check; just run and print the result

KNOWN LIMITATION (verified against a live logs-parser, 2026-09-16):
POST /pipeline/test-function inserts your snippet BEFORE the pipeline's
built-in JSON auto-parsing stage, regardless of where you place functions
within your own snippet. A relabel `keep`/`drop` condition that reads an
auto-extracted facet (`@level`, `@path`, ...) will see an empty value here
and behave as if nothing matched — even though the same YAML is correct for
a real deployment, where you control the function's position in the full
`config` list directly. Examples affected by this are marked
`expect=manual` with a note; verify that specific behavior in a lower
environment instead of through this endpoint.

This validates that the examples in the Kloudfuse Log Parsing Configuration
docs work as described.

Usage:
    python3 validate_examples.py
    python3 validate_examples.py --only relabel
    python3 validate_examples.py --only relabel/replace --show-output
    python3 validate_examples.py --host localhost:7101
"""

import argparse
import base64
import json
import re
import sys
import time
from pathlib import Path
from typing import Optional

import requests

HERE = Path(__file__).resolve().parent

_MARKER_RE = re.compile(r"<!--\s*validation:\s*([^>]*?)\s*-->")
_YAML_BLOCK_RE = re.compile(r"```yaml\n(.*?)\n```", re.DOTALL)
_JSON_BLOCK_RE = re.compile(r"```json\n(.*?)\n```", re.DOTALL)


def parse_readme(path: Path):
    """Return (pipeline_yaml, payload_bytes, opts) from a README's example."""
    text = path.read_text(encoding="utf-8")
    marker = _MARKER_RE.search(text)
    opts = {}
    if marker:
        for kv in marker.group(1).split():
            if "=" in kv:
                k, v = kv.split("=", 1)
                opts[k] = v
    yaml_block = _YAML_BLOCK_RE.search(text, marker.end() if marker else 0)
    json_block = _JSON_BLOCK_RE.search(text, marker.end() if marker else 0)
    if not yaml_block or not json_block:
        return None, None, opts
    return yaml_block.group(1), json_block.group(1).encode("utf-8"), opts


def parse_labels(opts: dict) -> dict:
    """Parse `labels=key:value,key2:value2` from the marker into a dict."""
    raw = opts.get("labels", "")
    labels = {}
    for kv in raw.split(","):
        if ":" in kv:
            k, v = kv.split(":", 1)
            labels[k] = v
    return labels


def run_example(host: str, pipeline_yaml: str, payload_bytes: bytes, payload_type: str,
                 additional_labels: dict):
    # An empty (or comment-only) yaml block means "no additional function" —
    # call /pipeline/test against the currently loaded pipeline as-is, rather
    # than merging an empty document through /pipeline/test-function.
    is_empty = not pipeline_yaml.strip() or all(
        line.strip().startswith("#") or not line.strip() for line in pipeline_yaml.splitlines()
    )
    payload = {
        "payloadType": payload_type,
        "data": base64.b64encode(payload_bytes).decode("ascii"),
        "ingestTimestamp": int(time.time() * 1000),
        "additionalLabels": additional_labels,
    }
    if is_empty:
        body = {"payload": payload}
        endpoint = "test"
    else:
        body = {"pipelineYaml": pipeline_yaml, "payload": payload}
        endpoint = "test-function"
    try:
        resp = requests.post(f"http://{host}/pipeline/{endpoint}", json=body, timeout=30)
        if resp.status_code != 200:
            return "FAIL", resp.text[:300], None
        result = resp.json()
    except Exception as exc:  # noqa: BLE001 — report any transport error
        return "FAIL", str(exc)[:300], None

    if not result.get("success"):
        error = result.get("error", "unknown error")
        # A dropped event is a successful outcome for drop/keep/dropLogLine
        # examples, reported as success=false with this exact message —
        # verified against a live logs-parser. Any other failure is a real
        # transport/config error.
        if error == "Event was dropped by the pipeline":
            return "DROPPED", error, None
        return "FAIL", error[:300], None

    data = result.get("result") or {}
    return "OK", "", data


def check_expectation(status: str, data: Optional[dict], opts: dict):
    """Return (status, detail) given the run outcome and the README's `expect=` option."""
    expect = opts.get("expect")
    if not expect or expect == "manual":
        return "MANUAL", ""

    if expect == "dropped":
        return ("PASS", "") if status == "DROPPED" else ("FAIL", f"expected the event to be dropped, got status={status}")
    if status == "DROPPED":
        return "FAIL", "event was unexpectedly dropped by the pipeline"

    kind, _, rest = expect.partition(":")
    if kind == "facet":
        name, _, value = rest.partition("=")
        actual = (data.get("facets") or {}).get(name)
        return ("PASS", "") if str(actual) == value else ("FAIL", f"facets[{name}]={actual!r}, want {value!r}")
    if kind == "tag":
        name, _, value = rest.partition("=")
        actual = (data.get("tags") or {}).get(name)
        return ("PASS", "") if str(actual) == value else ("FAIL", f"tags[{name}]={actual!r}, want {value!r}")
    if kind == "level":
        actual = data.get("logLevel")
        return ("PASS", "") if actual == rest else ("FAIL", f"logLevel={actual!r}, want {rest!r}")
    if kind == "fingerprint":
        actual = data.get("fingerprintString") or ""
        return ("PASS", "") if rest in actual else ("FAIL", f"fingerprintString={actual!r} does not contain {rest!r}")
    return "FAIL", f"unrecognized expect kind: {kind!r}"


def find_examples(only: Optional[str]):
    for readme in sorted(HERE.glob("*/*/README.md")):
        rel = readme.relative_to(HERE).parent.as_posix()
        if only and not rel.startswith(only):
            continue
        yield rel, readme


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate logs-parser-config examples against a live logs-parser.")
    parser.add_argument("--host", default="localhost:7101",
                         help="logs-parser host:port (default: localhost:7101, after kubectl port-forward)")
    parser.add_argument("--only", help="Only run examples under this category or category/function path")
    parser.add_argument("--payload-type", default="datadog", help="Agent payload format (default: datadog)")
    parser.add_argument("--show-output", action="store_true", help="Print the parsed result for each example")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds to sleep between requests (default: 0.5)")
    args = parser.parse_args()

    results = {"PASS": 0, "FAIL": 0, "MANUAL": 0}
    for name, readme in find_examples(args.only):
        pipeline_yaml, payload_bytes, opts = parse_readme(readme)
        if pipeline_yaml is None:
            print(f"  SKIP   {name}  (no yaml/json example blocks found)")
            continue

        run_status, detail, data = run_example(args.host, pipeline_yaml, payload_bytes, args.payload_type,
                                                parse_labels(opts))
        if run_status == "FAIL":
            print(f"  FAIL   {name}  {detail}")
            results["FAIL"] += 1
        else:
            status, detail = check_expectation(run_status, data, opts)
            print(f"  {status:<6} {name}  {detail}")
            results[status] += 1
            if args.show_output:
                print(f"         {json.dumps(data, sort_keys=True)[:300]}")

        time.sleep(args.delay)

    print(f"\n{results['PASS']} passed, {results['FAIL']} failed, {results['MANUAL']} manual")
    sys.exit(1 if results["FAIL"] else 0)


if __name__ == "__main__":
    main()
