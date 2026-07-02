# cos

Returns the cosine of a number given in radians. The result is always in the range `[-1, 1]`.

## Syntax

```fuseql
| cos(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value, interpreted as radians. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute `cos(0)` = 1.0 and `cos(π)` ≈ -1.0.

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| cos(0) as cos_0, cos(3.14159) as cos_pi
```

**Expected output:**

| _timeslice | cos_0 | cos_pi |
|---|---|---|
| 2026-06-27 18:00:00 UTC | 1.0 | -1.0 |
| 2026-06-27 19:00:00 UTC | 1.0 | -1.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | cos(0) as cos_0, cos(3.14159) as cos_pi\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `cos(0)` = 1.0. `cos(π/2)` ≈ 0. `cos(π)` ≈ -1.0.
- To convert degrees to radians before calling `cos`, multiply by `3.14159 / 180`.
- All FuseQL trigonometric operators work in radians.
