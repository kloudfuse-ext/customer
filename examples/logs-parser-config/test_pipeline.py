#!/usr/bin/env python3
"""
test_pipeline.py — Test a logs-parser pipeline config against a sample payload.

Calls the logs-parser Pipeline API (port 7101, in-cluster only):

    GET  /pipeline/info           show the currently loaded pipeline
    POST /pipeline/test           run the currently loaded pipeline against a payload
    POST /pipeline/test-function  merge a pipeline YAML snippet with the loaded
                                   pipeline, then run the merged pipeline against a payload

This is how you test a `kf_parsing_config` change (relabel/transform rule, dissect
or grok pattern, and so on) before adding it to Helm values and redeploying — see
the "Testing a pipeline change before deploying" section of the Log Parsing
Configuration docs.

The service isn't exposed outside the cluster by default. Port-forward it first:

    kubectl port-forward svc/logs-parser 7101:7101

Usage:
    # Show the currently loaded pipeline
    python3 test_pipeline.py --info

    # Test the currently loaded pipeline against a payload file
    python3 test_pipeline.py --payload-file payload.json --payload-type datadog

    # Test a pipeline snippet merged with the loaded pipeline
    python3 test_pipeline.py --pipeline-file pipeline.yaml \\
        --payload-file payload.json --payload-type datadog

    # Read the payload from stdin instead of a file
    echo '{"message": "2024-01-16 ERROR boom", "ddsource": "myapp"}' \\
      | python3 test_pipeline.py --pipeline-file pipeline.yaml --payload-type datadog
"""

import argparse
import base64
import json
import sys
import time
from pathlib import Path
from typing import Optional

import requests

JSON_PAYLOAD_TYPES = {"datadog", "fluent-bit-json", "fluentd-json", "otlp-json"}


def show_info(host: str) -> None:
    resp = requests.get(f"http://{host}/pipeline/info", timeout=30)
    resp.raise_for_status()
    body = resp.json()
    yaml_text = body.get("userDefinedYaml")
    if yaml_text:
        print(yaml_text)
    else:
        print("(no custom pipeline configured — running with built-in defaults only)", file=sys.stderr)


def read_payload(payload_file: Optional[str]) -> bytes:
    if payload_file:
        return Path(payload_file).read_bytes()
    if sys.stdin.isatty():
        print("error: provide --payload-file or pipe payload JSON on stdin", file=sys.stderr)
        sys.exit(1)
    return sys.stdin.buffer.read()


def run_test(host: str, payload_type: str, payload_bytes: bytes,
             additional_labels: dict, pipeline_yaml: Optional[str]) -> dict:
    if payload_type not in JSON_PAYLOAD_TYPES:
        print(f"error: --payload-type must be one of {sorted(JSON_PAYLOAD_TYPES)} "
              f"(binary agent formats can't be tested through this API)", file=sys.stderr)
        sys.exit(1)

    body = {
        "payload": {
            "payloadType": payload_type,
            "data": base64.b64encode(payload_bytes).decode("ascii"),
            "ingestTimestamp": int(time.time() * 1000),
            "additionalLabels": additional_labels,
        }
    }
    if pipeline_yaml is not None:
        body["pipelineYaml"] = pipeline_yaml
        endpoint = "test-function"
    else:
        endpoint = "test"

    resp = requests.post(f"http://{host}/pipeline/{endpoint}", json=body, timeout=30)
    resp.raise_for_status()
    return resp.json()


def main() -> None:
    parser = argparse.ArgumentParser(description="Test a logs-parser pipeline config against a sample payload.")
    parser.add_argument("--host", default="localhost:7101",
                         help="logs-parser host:port (default: localhost:7101, after kubectl port-forward)")
    parser.add_argument("--info", action="store_true", help="Print the currently loaded pipeline YAML and exit")
    parser.add_argument("--pipeline-file", help="YAML file with the pipeline function(s) to test; "
                                                 "omit to test the currently loaded pipeline as-is")
    parser.add_argument("--payload-file", help="JSON file with the raw agent payload to test against")
    parser.add_argument("--payload-type", default="datadog", choices=sorted(JSON_PAYLOAD_TYPES),
                         help="Agent payload format (default: datadog)")
    parser.add_argument("--label", action="append", default=[], metavar="KEY=VALUE",
                         help="Additional label to attach to the payload; repeatable")
    args = parser.parse_args()

    if args.info:
        show_info(args.host)
        return

    additional_labels = {}
    for kv in args.label:
        if "=" not in kv:
            print(f"error: --label must be KEY=VALUE, got {kv!r}", file=sys.stderr)
            sys.exit(1)
        k, v = kv.split("=", 1)
        additional_labels[k] = v

    pipeline_yaml = Path(args.pipeline_file).read_text() if args.pipeline_file else None
    payload_bytes = read_payload(args.payload_file)

    result = run_test(args.host, args.payload_type, payload_bytes, additional_labels, pipeline_yaml)
    print(json.dumps(result, indent=2))
    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
