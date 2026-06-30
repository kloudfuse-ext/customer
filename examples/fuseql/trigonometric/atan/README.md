# atan

Returns the arctangent (inverse tangent) of a number, in radians. The result is always in the range `(-π/2, π/2)`. Accepts any real-valued input — no domain restriction.

## Syntax

```fuseql
| atan(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. Accepts any real number. |
| `as <alias>` | Required | Output column name for the result, in radians. |

## Example

Compute `atan(1.0)`, which is π/4 radians (45°).

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| atan(1.0) as angle_rad
```

**Expected output:**

| _timeslice | angle_rad |
|---|---|
| 2026-06-27 18:00:00 UTC | 0.7854 |
| 2026-06-27 19:00:00 UTC | 0.7854 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | atan(1.0) as angle_rad\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `atan(1.0)` = 0.7854 rad (π/4, 45°). `atan(0)` = 0. As input → ∞, result approaches π/2 (~1.5708).
- Unlike `asin` and `acos`, `atan` accepts any real number.
- All FuseQL trigonometric operators work in radians. Multiply by `180 / 3.14159` to convert to degrees.
