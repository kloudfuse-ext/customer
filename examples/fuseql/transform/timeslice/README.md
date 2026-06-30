# timeslice

Buckets each event's timestamp into fixed-width time windows for use in time-series aggregation. The bucket value is exposed as `_timeslice` (epoch milliseconds) and is the standard grouping field for log-based time-series aggregations.

## Syntax

```fuseql
| timeslice <duration>
| timeslice <duration> as <alias>
```

`<duration>` accepts FuseQL duration literals such as `1m`, `5m`, `1h`, `1d`, `7d`. When `as <alias>` is omitted, the bucket field is named `_timeslice`.

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<duration>` | Required | Width of each time bucket (e.g., `1m`, `5m`, `1h`). |
| `as <alias>` | Optional | Custom name for the bucket field. Defaults to `_timeslice`. |

## Example

Count nginx requests per 1-minute bucket.

```fuseql
source="nginx"
| timeslice 1m
| count by _timeslice
```

**Expected output:**

| _timeslice | _count |
|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 |
| 2026-06-27 18:54:00 UTC | 650,712 |
| 2026-06-27 18:55:00 UTC | 474,040 |
| 2026-06-27 18:56:00 UTC | 364,655 |
| 2026-06-27 18:57:00 UTC | 222,961 |
| 2026-06-27 18:58:00 UTC | 94,458 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count by _timeslice\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `_timeslice` is the bucket's **right (upper) edge**, expressed as epoch milliseconds in UTC.
- Buckets are anchored to the Unix epoch, not calendar boundaries. `timeslice 7d` boundaries always fall on a Thursday (1970-01-01 was a Thursday).
- Multi-day durations (`2d`, `7d`) do not align to calendar weeks or months.
- Window operators (`accum`, `rollingstd`, `smooth`, `total`) and algorithm operators expect a `timeslice`-produced series upstream.
