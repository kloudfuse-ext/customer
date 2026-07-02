# sin

Returns the sine of a number given in radians. The result is always in the range `[-1, 1]`.

## Syntax

```fuseql
| sin(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value, interpreted as radians. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute `sin(0)` = 0.0 and `sin(π/2)` = 1.0.

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| sin(0) as sin_0, sin(1.5708) as sin_halfpi
```

**Expected output:**

| _timeslice | sin_0 | sin_halfpi |
|---|---|---|
| 2026-06-27 18:00:00 UTC | 0.0 | 1.0 |
| 2026-06-27 19:00:00 UTC | 0.0 | 1.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | sin(0) as sin_0, sin(1.5708) as sin_halfpi\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `sin(0)` = 0.0. `sin(π/2)` = 1.0. `sin(π)` ≈ 0 (floating-point rounding may give a very small non-zero value).
- To convert degrees to radians, multiply by `3.14159 / 180`.
