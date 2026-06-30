# abs

Returns the absolute value of a number. Negative values become positive; non-negative values are unchanged. Use `abs` to normalize signed fields — such as latency deltas or signed error margins — before computing aggregations.

## Syntax

```fuseql
| abs(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Count nginx requests per 1-minute bucket and compute the absolute value of each bucket's count.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| abs(requests) as abs_requests
```

**Expected output:**

| _timeslice | requests | abs_requests |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 61,441 |
| 2026-06-27 18:54:00 UTC | 650,712 | 650,712 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | abs(requests) as abs_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `abs` is most useful when applied to fields that may hold negative values, such as the difference between two metrics (`actual - expected`).
- Applying `abs` to a count or sum that is always positive is safe but has no practical effect.
- For counts derived from `timeslice`, the result equals the count itself since counts are always non-negative.
