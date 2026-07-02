# expm1

Returns `exp(x) − 1` with higher numerical precision than computing `exp(x) - 1` directly. When x is very close to zero, `expm1` avoids floating-point cancellation errors.

## Syntax

```fuseql
| expm1(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. Most useful for inputs near zero. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute a precision-safe exponential growth factor from a normalized request rate.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| expm1(requests / 1000000) as growth_factor
```

**Expected output:**

| _timeslice | requests | growth_factor |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 0.0634 |
| 2026-06-27 18:54:00 UTC | 650,712 | 0.9164 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | expm1(requests / 1000000) as growth_factor\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `expm1(1)` returns `1.71828` (i.e., e − 1).
- For inputs very close to zero (e.g., rates or probabilities like `0.000001`), `expm1` is significantly more accurate than `exp(x) - 1`.
- Use `expm1` when converting small per-unit growth rates to absolute multipliers.
