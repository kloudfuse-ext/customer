# sqrt

Returns the square root of a number. Use `sqrt` to compress wide-ranging metrics into a more uniform scale without collapsing low-traffic values the way a logarithm would.

## Syntax

```fuseql
| sqrt(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A non-negative numeric field name or literal value. Negative inputs return `NaN`. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Normalize nginx request counts using the square root before plotting on a shared chart axis.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| sqrt(requests) as sqrt_requests
```

**Expected output:**

| _timeslice | requests | sqrt_requests |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 247.87 |
| 2026-06-27 18:54:00 UTC | 650,712 | 806.67 |
| 2026-06-27 18:55:00 UTC | 474,040 | 688.51 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | sqrt(requests) as sqrt_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `sqrt(16)` returns `4.0`.
- For cube root compression, use `cbrt`. For logarithmic compression, use `log` or `log10`.
- `sqrt` is a good middle ground: less compression than a logarithm, more than a cube root.
- Guard against negative inputs with `| where requests >= 0` if negative values are possible.
