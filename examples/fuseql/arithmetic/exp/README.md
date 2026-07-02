# exp

Returns Euler's number *e* (~2.71828) raised to the power of a number. Use `exp` to reverse a natural logarithm transformation — converting `log`-scaled metrics back to their original linear scale.

## Syntax

```fuseql
| exp(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. Large inputs (above ~700) will overflow to infinity. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Apply `log` to compress request counts, then reverse with `exp` to recover the original scale.

```fuseql
source="nginx"
| timeslice 5m
| count as requests by _timeslice
| log(requests) as log_requests
| exp(log_requests) as recovered_requests
```

**Expected output:**

| _timeslice | log_requests | recovered_requests |
|---|---|---|
| 2026-06-27 18:50:00 UTC | 13.01 | 449,628.0 |
| 2026-06-27 18:55:00 UTC | 13.39 | 652,847.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 5m | count as requests by _timeslice | log(requests) as log_requests | exp(log_requests) as recovered_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `exp(1)` returns `2.71828`. `exp(3)` returns `20.09`.
- Do not apply `exp` directly to raw request counts (hundreds of thousands) — this overflows. Apply it only to log-transformed or small-valued fields.
- The inverse of `exp` is `log`.
