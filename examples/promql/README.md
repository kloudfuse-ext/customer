# PromQL API Examples

Examples for querying Kloudfuse metrics programmatically with **PromQL**.
Kloudfuse serves the standard Prometheus HTTP API, so any
Prometheus-compatible client (Grafana, `promtool`, curl) works unchanged.

## Prerequisites

```bash
pip install requests
```

## Configuration

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=glsa_...
```

## Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /api/v1/query` | Instant queries — evaluate at one point in time |
| `GET /api/v1/query_range` | Range queries — evaluate at every step over a range |
| `GET /api/v1/labels` | List label names |
| `GET /api/v1/label/<name>/values` | List values for a label |
| `GET /api/v1/series` | List series matching a selector |

## Scripts

### `query_metrics.py` — Run a PromQL query

```bash
# Top services by goroutine count, evaluated once
python3 query_metrics.py --instant \
  --query 'topk(3, sum by (app_kubernetes_io_name) (go_goroutines))'

# Ingester Kafka consumption rate over the last 30 minutes
python3 query_metrics.py \
  --query 'sum(rate(ingester_kafka_batch_length_count[5m]))' \
  --minutes 30 --step 60
```

### `validate_examples.py` — Run every documented example

Walks the per-operator directories (`<category>/<operator>/README.md`),
extracts each fenced ` ```promql ` example block, runs it against the
cluster, and reports PASS / EMPTY / FAIL. This validates that the examples
in the Kloudfuse PromQL documentation work as described.

```bash
python3 validate_examples.py
python3 validate_examples.py --only counter
python3 validate_examples.py --only counter/rate --show-output
```

## Operator examples

One directory per documented PromQL operator, mirroring the Kloudfuse docs
(Query Languages → PromQL). Category names follow the FuseQL/LogQL docs
vocabulary where a counterpart exists.

| Category | Operators |
|---|---|
| `comparison/` | `=`, `!=`, `=~`, `!~` label matchers |
| `selector/` | range vector `[5m]`, `offset`, `@`, subqueries |
| `binary-operator/` | arithmetic, comparison, set ops, vector matching |
| `aggregation/` | `sum`, `avg`, `min`, `max`, `count`, `count_values`, `group`, `stddev`, `stdvar`, `quantile`, `topk`, `bottomk` |
| `counter/` | `rate`, `irate`, `increase`, `resets` |
| `trend/` | `delta`, `idelta`, `deriv`, `predict_linear`, `double_exponential_smoothing`, `changes` |
| `over-time/` | `*_over_time`, `absent_over_time`, `present_over_time` |
| `arithmetic/` | `abs`, `ceil`, `floor`, `round`, `exp`, `ln`, `log2`, `log10`, `sqrt`, `sgn`, `clamp` family |
| `trigonometric/` | `sin` … `atanh`, `deg`, `rad`, `pi` |
| `datetime/` | `time`, `timestamp`, `minute` … `year` |
| `transform/` | `label_replace`, `label_join`, `sort`, `sort_desc` |
| `misc/` | `absent`, `scalar`, `vector`, `histogram_quantile`, `apdex` |
| `algorithm/` | `sarima`, `seasonal_decompose`, `dbscan`, `kf_rolling_quantile`, `seasonal_forecast`, `prophet` (Kloudfuse advance functions) |
