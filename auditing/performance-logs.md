# Performance Log Examples

All queries use `source="kf-performance-log"` as the base filter.

---

## Total query volume

```fuseql
source="kf-performance-log" | count
```

**Validated** — `<your-kloudfuse-hostname>`, 30-day window (2026-06-17 → 2026-07-17):

| _count |
|---|
| 1,691,382 |

**Validated** — `<your-kloudfuse-hostname>`, 24-hour window (2026-07-16 → 2026-07-17):

| _count |
|---|
| 249,660 |

---

## Query volume by service

Shows which query services are handling the most requests. Use this to understand platform
load distribution across telemetry types.

```fuseql
source="kf-performance-log" | count by service_name
```

**Validated** — `<your-kloudfuse-hostname>`, 30-day window (2026-06-17 → 2026-07-17):

| service_name | _count |
|---|---|
| `query-service` | 1,502,168 |
| `logs-query-service` | 177,794 |
| `events-query-service` | 10,844 |
| `trace-query-service` | 334 |
| `rum-query-service` | 231 |

**Validated** — `<your-kloudfuse-hostname>`, 24-hour window (2026-07-16 → 2026-07-17):

| service_name | _count |
|---|---|
| `query-service` | 212,303 |
| `logs-query-service` | 35,252 |
| `events-query-service` | 2,101 |
| `trace-query-service` | 4 |

`query-service` accounts for ~89% of all queries because it handles every PromQL request —
including dashboard panel refreshes and alert evaluation cycles. Every alert that fires or
evaluates generates one or more `query-service` entries.

---

## Query volume by user

Ranks callers by number of queries issued. Rows with an empty `user_email` are alert
evaluation queries and internal service-to-service calls — these represent the majority
of volume on most clusters.

```fuseql
source="kf-performance-log" | count by user_email
```

**Illustrative output** (expected for a cluster with active users and alerting):

| user_email | _count |
|---|---|
| (empty — alert evaluation / internal) | 201,450 |
| `analyst@example.com` | 19,341 |
| `alice@example.com` | 8,204 |
| `dashboard-svc@example.com` | 4,871 |
| `bob@example.com` | 1,285 |

### Queries from a specific user

```fuseql
source="kf-performance-log" user_email="analyst@example.com" | count by service_name
```

**Illustrative output**:

| service_name | _count |
|---|---|
| `query-service` | 14,203 |
| `logs-query-service` | 4,891 |
| `events-query-service` | 247 |

---

## Average query latency by user

Identifies users whose queries take the longest on average. High latency for a specific
user often indicates broad time-range or high-cardinality queries.

```fuseql
source="kf-performance-log" | avg(duration_ms) by user_email
```

**Illustrative output**:

| user_email | _avg |
|---|---|
| `analyst@example.com` | 4,231 |
| `alice@example.com` | 892 |
| `dashboard-svc@example.com` | 341 |
| `bob@example.com` | 218 |

---

## Slow queries exceeding a threshold

Counts queries over a given duration, grouped by service. Adjust the threshold to match
your SLOs — common starting points are 2000ms for dashboard panels and 5000ms for
ad-hoc queries.

```fuseql
source="kf-performance-log" duration_ms > 5000 | count by service_name
```

**Illustrative output**:

| service_name | _count |
|---|---|
| `query-service` | 1,847 |
| `logs-query-service` | 312 |
| `trace-query-service` | 28 |

---

## p95 latency by service

The 95th-percentile captures tail latency without being skewed by extreme outliers. Use
this alongside averages to find services where most queries are fast but a significant
tail is slow.

```fuseql
source="kf-performance-log" | p95(duration_ms) by service_name
```

**Illustrative output**:

| service_name | _p95 |
|---|---|
| `trace-query-service` | 8,104 |
| `query-service` | 3,217 |
| `logs-query-service` | 1,893 |
| `events-query-service` | 644 |
| `rum-query-service` | 201 |

---

## Query volume over time

Plots query throughput in hourly buckets. Use this to identify traffic spikes, alert
evaluation storms, or the effect of scheduled dashboard loads.

```fuseql
source="kf-performance-log" | count by service_name | timeslice 1h
```

Returns a time-series table with one row per service per hour bucket.

---

## Log field reference

### Facets

These fields are indexed and appear in the Logs UI Facets panel.

| Field | Type | Description |
|---|---|---|
| `user_email` | string | Email of the user who issued the query. Empty for alert evaluation and service-to-service calls. |
| `duration_ms` | integer | End-to-end query duration in milliseconds, measured at the service boundary including Pinot execution time. |
| `service_name` | string | The query service that handled the request: `query-service`, `logs-query-service`, `events-query-service`, `trace-query-service`, `rum-query-service`. |
| `request_id` | string | Unique request identifier for cross-service correlation with other log streams. |

---

## API call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <sa-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"kf-performance-log\\\" | count by service_name\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```
