# log

Returns the natural logarithm (base *e*) of a number. Use `log` to compress wide-ranging metrics into a scale that is easier to visualize and compare.

## Syntax

```fuseql
| log(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A positive numeric field name or literal value. Zero or negative inputs return `NaN` or `-Infinity`. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compress nginx request counts onto a natural log scale for trend analysis.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| log(requests) as log_requests
```

**Expected output:**

| _timeslice | requests | log_requests |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 11.03 |
| 2026-06-27 18:54:00 UTC | 650,712 | 13.39 |
| 2026-06-27 18:55:00 UTC | 474,040 | 13.07 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | log(requests) as log_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `log(10)` returns `2.30258` — not `1`. For base-10 logarithms use `log10`.
- To reverse the transformation, apply `exp`.
- Input must be strictly positive. Guard with `| where requests > 0` if zero counts are possible.
