# LogQL API Examples

Examples for querying Kloudfuse logs programmatically with **LogQL**, Grafana
Loki's query language. Kloudfuse serves the standard Loki HTTP API, so any
Loki-compatible client (Grafana, `logcli`, curl) works unchanged.

## Prerequisites

```bash
pip install requests
```

## Configuration

Set your Kloudfuse host and Service Account token:

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=glsa_...
```

Or pass them directly as arguments (see `--help` on each script).

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /loki/api/v1/query_range` | Range queries — log lines or metrics over a time range |
| `GET /loki/api/v1/query` | Instant queries — metric value at a single point in time |
| `GET /loki/api/v1/labels` | List label names |
| `GET /loki/api/v1/label/<name>/values` | List values for a label |
| `GET /loki/api/v1/series` | List series matching a selector |

## Scripts

### `fetch_logs.py` — Raw log retrieval

Runs a LogQL *log query* (stream selector + pipeline, no metric wrapper)
through `/loki/api/v1/query_range` and prints matching lines.

```bash
# Fetch nginx POST requests from the last 10 minutes
python3 fetch_logs.py --query '{source="nginx"} |= "POST"' --minutes 10

# Parse grafana logfmt and keep only slow responses, as JSON Lines
python3 fetch_logs.py \
  --query '{source="grafana"} |= "duration=" | logfmt | duration > 100ms' \
  --minutes 30 --output slow.jsonl
```

### `query_metrics.py` — Log-based metrics

Runs a LogQL *metric query* (range aggregation, optionally wrapped in vector
aggregations and binary operators). Use `--instant` for a single evaluation
at the current time, or omit it for a range query with `--step`.

```bash
# Log volume by level, evaluated once (instant)
python3 query_metrics.py --instant \
  --query 'sum by (level) (count_over_time({source="grafana"}[5m]))'

# p95 Loki datasource latency over the last hour, 1-minute resolution
python3 query_metrics.py \
  --query 'quantile_over_time(0.95, {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m]) by (endpoint)' \
  --minutes 60 --step 60
```

### `validate_examples.py` — Run every documented example

Walks the per-operator directories (`<category>/<operator>/README.md`),
extracts each fenced ` ```logql ` example block, runs it against the cluster,
and reports PASS / EMPTY / FAIL. This validates that the examples in the
Kloudfuse LogQL documentation work as described.

```bash
# Validate everything (paced to be gentle on the cluster)
python3 validate_examples.py

# Validate one category or one operator
python3 validate_examples.py --only parse
python3 validate_examples.py --only parse/json

# Show the returned data for each query
python3 validate_examples.py --only unwrap --show-output
```

## Operator examples

One directory per documented LogQL operator, mirroring the Kloudfuse docs
(Query Languages → LogQL). Each `README.md` contains the operator's syntax,
parameters, a worked example with expected output, and a copy-paste `curl`
API call.

Category names match the Kloudfuse FuseQL docs vocabulary where a
counterpart exists.

| Category | Operators |
|---|---|
| `comparison/` | `=`, `!=`, `=~`, `!~` stream-selector label matchers |
| `text-search/` | `\|=`, `!=`, `\|~`, `!~`, `\|>`, `!>`, `or` line filters |
| `parse/` | `json`, `logfmt`, `pattern`, `regexp`, `unpack` |
| `predicate/` | string, numeric, duration, bytes, `and`/`or` label filters |
| `transform/` | `line_format`, `label_format`, `decolorize`, `drop`, `keep` |
| `range-aggregation/` | `count_over_time`, `rate`, `bytes_over_time`, `bytes_rate`, `absent_over_time` |
| `unwrap/` | `unwrap`, `*_over_time` statistics |
| `aggregation/` | `sum`, `avg`, `min`, `max`, `count`, `stddev`, `stdvar`, `topk`, `bottomk`, `sort`, `sort_desc` |
| `binary-operator/` | arithmetic, comparison, set operations |
| `misc/` | `label_replace`, `vector` |
