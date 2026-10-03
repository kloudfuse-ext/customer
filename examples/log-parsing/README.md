# Log Parsing Examples

Runnable, local examples for the Kloudfuse logs-parser configuration
(`kf_parsing_config` in the `logs-parser` Helm values) documented in the
Kloudfuse docs under Data Management -> Log Parsing.

Unlike the `logql/`, `fuseql/`, `promql/`, and `traceql/` example sets in this
repo, log parsing config takes effect only after a `logs-parser` Helm upgrade
(see the docs' Architecture page, "Deploying a change requires a redeploy") —
there's no customer-facing query API to test a change against. The
`grammar/` and `relabel/` recipes below are validated entirely offline: each
tester locally reimplements the documented behavior of one pipeline function
(`dissect`, `grok`, `relabel`/`transform`), so you can check a config
snippet's shape against a sample log line before you paste it into Helm
values and deploy.

The `troubleshooting/` and `performance/` recipes are different: they
demonstrate bugs and pitfalls that depend on pipeline-level behavior (stage
ordering, condition scoping across multiple functions, JSON auto-parsing's
facet ceiling) that a single-action local simulator can't reproduce. Those
are verified directly against a running cluster — via the Pipeline API's
`/pipeline/test-function` endpoint for the config-correctness ones, and via
the platform's own PromQL metrics for the performance one — with the actual
captured results documented in each README.

These are approximations of the production engine for the common cases, not
a byte-for-byte reimplementation — they don't cover every edge case (see each
tester's module docstring for what's out of scope, e.g. `%{&ref}` dissect
references). Confirm exact behavior against a running cluster when it matters.

## Prerequisites

```bash
pip install pygrok
```

(`dissect_tester.py` and `relabel_tester.py` use only the standard library.)

## Scripts

### `dissect_tester.py` — Test a dissect tokenizer

```bash
python3 dissect_tester.py \
  --tokenizer '%{sourceIp} - - [%{timestamp}] "%{requestMethod} %{uri} %{_}" %{responseCode} %{contentLength}' \
  --line '10.12.0.35 - - [26/May/2021:18:59:10 +0000] "GET /unavailable HTTP/1.1" 503 21'
```

### `grok_tester.py` — Test a grok pattern

```bash
python3 grok_tester.py \
  --pattern '%{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} %{GREEDYDATA:msg}' \
  --line '2024-01-16T10:30:00Z ERROR Connection failed'
```

### `relabel_tester.py` — Test a relabel/transform rule

```bash
python3 relabel_tester.py \
  --args '{"action": "facet_to_label_map", "sourceLabels": "@eventSource", "targetLabel": "source"}' \
  --facets '{"eventSource": "awsLogSource"}' --labels '{}'
```

### `validate_examples.py` — Run every documented example

Walks the per-recipe directories (`<category>/<recipe>/README.md`), extracts
each recipe's validation fixture, and reports PASS / FAIL.

```bash
python3 validate_examples.py
python3 validate_examples.py --only grammar/dissect-nginx-access-log
python3 validate_examples.py --only relabel
```

## Recipes

| Category | Recipe | Demonstrates |
|---|---|---|
| `grammar/` | `dissect-nginx-access-log` | Extracting multiple facets from a delimited text line with `dissect` |
| `grammar/` | `dissect-pinot-segment` | A literal prefix/suffix pattern with `dissect`, scoped with a `contains` condition |
| `grammar/` | `grok-app-log` | Extracting a timestamp, level, and message with named `grok` patterns |
| `relabel/` | `add-static-label` | Tagging every matching log line with a fixed label (`replace`) |
| `relabel/` | `drop-healthcheck-lines` | Discarding noisy log lines entirely (`drop`) |
| `relabel/` | `promote-facet-to-label` | Promoting an extracted facet to an always-indexed label (`transform` + `facet_to_label_map`) |
| `troubleshooting/` | `dissect-wrong-delimiter` | A wrong delimiter produces wrong facets silently, not an error |
| `troubleshooting/` | `relabel-vs-transform-facet` | A `facet_to_label_map` promotion silently does nothing written as `relabel` instead of `transform` |
| `troubleshooting/` | `unscoped-drop-wrong-source` | An unscoped `conditions` block drops lines from a source it wasn't meant for |
| `troubleshooting/` | `json-facet-ceiling` | JSON auto-parsing's 50-facet ceiling is all-or-nothing — 51 fields produces 0 facets, not 50 (kloudfuse/bugzilla#1701) |
| `performance/` | `too-many-rules` | Confirmed ~28x CPU increase from 2,000 no-op rules, with zero change in log volume |
