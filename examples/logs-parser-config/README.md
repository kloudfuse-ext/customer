# Log Parsing Configuration Examples

Working `kf_parsing_config` pipeline snippets for the Kloudfuse `logs-parser`
service — relabeling, dissect/grok grammar, JSON auto-parsing controls, and
the other pipeline functions. Each example is a self-contained YAML function
plus a sample agent payload, tested through `logs-parser`'s own Pipeline API
rather than a live query language, so you can confirm a change works before
adding it to Helm values and redeploying.

## Prerequisites

```bash
pip install requests
```

`logs-parser`'s Pipeline API (port 7101) isn't exposed outside the cluster by
default. Port-forward it first:

```bash
kubectl port-forward svc/logs-parser 7101:7101
```

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /pipeline/info` | Show the currently loaded pipeline YAML |
| `POST /pipeline/test` | Run the currently loaded pipeline against a payload |
| `POST /pipeline/test-function` | Merge a pipeline YAML snippet with the loaded pipeline, then run it against a payload |

Only JSON-based agent payload types are testable this way: `datadog`,
`fluent-bit-json`, `fluentd-json`, `otlp-json`. Binary formats (`otlp-proto`,
`fluent-bit`, `fluentd`, `filebeat`, `kinesis`, `heroku`) aren't supported by
this API.

## Scripts

### `test_pipeline.py` — Test one pipeline snippet by hand

```bash
# Show the currently loaded pipeline
python3 test_pipeline.py --info

# Test a snippet against a sample Datadog payload
python3 test_pipeline.py --pipeline-file relabel/replace/pipeline.yaml \
  --payload-file relabel/replace/payload.json --payload-type datadog
```

### `validate_examples.py` — Run every documented example

Walks the per-function directories (`<category>/<function>/README.md`),
extracts each example's ` ```yaml ` pipeline snippet and ` ```json ` sample
payload, runs them through `/pipeline/test-function`, and reports
PASS / FAIL / MANUAL against the expectation declared in the README.

```bash
# Validate everything
python3 validate_examples.py

# Validate one category or one function
python3 validate_examples.py --only relabel
python3 validate_examples.py --only relabel/replace

# Show the parsed result for each example
python3 validate_examples.py --only grammar --show-output
```

## Function examples

One directory per documented `kf_parsing_config` function, mirroring the
Kloudfuse docs (Data Management → Log Parsing → Configuration). Each
`README.md` contains the function's parameters, a worked example with
expected output, and a copy-paste way to test it.

| Category | Functions |
|---|---|
| `relabel/` | `replace`, `drop`, `keep`, `label_map`, `facet_to_label_map` (also used by `transform`) |
| `grammar/` | `dissect`, `grok` |
| `json/` | automatic JSON facet extraction, `skipAutoFacet` |
| `other-functions/` | `addFacet`, `setLogLevel`, `dropLogLine`, `logFmt` |

`relabel` and `transform` are the same engine and action set, just
conventionally placed at different points in the function list — see
`relabel/facet-to-label/README.md` for the promote-a-facet-to-a-label example
that's usually written as `transform`.

For the full reference — every function's arguments, `conditions` syntax, and
where each fits in the pipeline — see the Kloudfuse docs: Data Management →
Log Parsing → Configuration, and Architecture.
