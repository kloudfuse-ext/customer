# log10

Returns the base-10 logarithm of a number. The result corresponds directly to the number of decimal digits in the original value, making it intuitive for metrics like request counts or byte sizes.

## Syntax

```fuseql
| log10(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A positive numeric field name or literal value. Zero or negative inputs return `NaN` or `-Infinity`. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute the base-10 log of nginx request counts. A result of 5.8 means the count is approximately 10^5.8 ≈ 630,000.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| log10(requests) as log10_requests
```

**Expected output:**

| _timeslice | requests | log10_requests |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 4.79 |
| 2026-06-27 18:54:00 UTC | 650,712 | 5.81 |
| 2026-06-27 18:55:00 UTC | 474,040 | 5.68 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | log10(requests) as log10_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `log10(10)` returns `1.0`. `log10(100)` returns `2.0`. `log10(600000)` returns approximately `5.78`.
- For natural logarithm (base e), use `log`. The relationship: `log10(x) = log(x) / log(10)`.
- Input must be strictly positive.
