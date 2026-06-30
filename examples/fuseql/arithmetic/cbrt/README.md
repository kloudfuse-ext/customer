# cbrt

Returns the cube root of a number. Use `cbrt` when you need to reverse a cubic scale or normalise data across an order-of-magnitude range where a square root would under-compress.

## Syntax

```fuseql
| cbrt(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. Negative inputs return a negative cube root. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compress the wide range of nginx traffic volumes using the cube root.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| cbrt(requests) as cbrt_requests
```

**Expected output:**

| _timeslice | requests | cbrt_requests |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 39.47 |
| 2026-06-27 18:54:00 UTC | 650,712 | 86.65 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | cbrt(requests) as cbrt_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `cbrt(27)` returns `3.0`. For very large volumes (hundreds of thousands), the cube root compresses values into the tens-to-hundreds range.
- Negative inputs are supported: `cbrt(-27)` returns `-3.0`.
- For square-root compression, use `sqrt`. For logarithmic compression, use `log` or `log10`.
