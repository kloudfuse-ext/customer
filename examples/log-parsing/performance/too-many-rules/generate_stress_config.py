#!/usr/bin/env python3
"""
generate_stress_config.py — Generate a kf_parsing_config overlay with N no-op
relabel rules, to reproduce the "too many configured rules slow the pipeline
down" scenario from the Kloudfuse troubleshooting guide.

Every generated rule is scoped to a source that will never appear
(`zzz-nonexistent-<i>`), so none of them ever actually match or change any
real log's output — the only effect is the per-line cost of evaluating each
rule's `conditions` block, which is exactly the mechanism being demonstrated.

WARNING: this is for a lower/disposable environment only. Deploying this
overlay measurably raises `logs-parser` CPU usage (confirmed: ~28x at 2,000
rules against a real cluster, with zero change in log volume). Never apply
it to a production deployment.

Usage:
    python3 generate_stress_config.py --rules 2000 --out stress.yaml
    helm upgrade kfuse <chart> -n <namespace> --reuse-values -f stress.yaml
    # ... observe via the PromQL queries below, then ...
    helm rollback kfuse <previous-revision> -n <namespace>

Query to observe the effect (run against your deployment's own Metrics
Explorer / PromQL API — see the troubleshooting guide's "Too many configured
rules" section):

    max(container_cpu_usage{kube_namespace="<namespace>", kube_container_name="logs-parser"})
"""

import argparse


def generate(n: int) -> str:
    lines = ["logs-parser:", "  kf_parsing_config:", "    config: |-"]
    for i in range(n):
        lines += [
            "      - relabel:",
            "          args:",
            '            - action: "replace"',
            f'            - regex: "zzz-stress-{i}"',
            '            - replacement: "unused"',
            f'            - targetLabel: "__stress_{i}"',
            "          conditions:",
            '            - matcher: "#source"',
            f'              value: "zzz-nonexistent-{i}"',
            '              op: "=="',
        ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--rules", type=int, default=2000, help="Number of no-op rules to generate (default: 2000)")
    parser.add_argument("--out", required=True, help="Output YAML file path")
    args = parser.parse_args()

    with open(args.out, "w") as f:
        f.write(generate(args.rules))
    print(f"Wrote {args.rules} rules to {args.out}")


if __name__ == "__main__":
    main()
