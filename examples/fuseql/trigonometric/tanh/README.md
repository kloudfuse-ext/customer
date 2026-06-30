# tanh

Returns the hyperbolic tangent of a number. Defined as `sinh(x) / cosh(x)`. Always returns a value in the range `(-1, 1)`.

## Syntax

```fuseql
| tanh(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. |
| `as <alias>` | Required | Output column name for the result. Always in the range `(-1, 1)`. |

## Example

Compute `tanh(0)` = 0.0.

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| tanh(0) as tanh_0
```

**Expected output:**

| _timeslice | tanh_0 |
|---|---|
| 2026-06-27 18:00:00 UTC | 0.0 |
| 2026-06-27 19:00:00 UTC | 0.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | tanh(0) as tanh_0\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `tanh(0)` = 0.0. `tanh(1)` ≈ 0.7616. For large positive inputs, `tanh` saturates near 1.0.
- Use `tanh` as a smooth sigmoidal squashing function to normalize unbounded fields into `(-1, 1)` without hard clipping.
