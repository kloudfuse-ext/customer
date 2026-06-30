# acos

Returns the arccosine (inverse cosine) of a number, in radians. The input must be in the range `[-1, 1]`.

## Syntax

```fuseql
| acos(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal in the range `[-1, 1]`. Values outside this range return `NaN`. |
| `as <alias>` | Required | Output column name for the result, in radians. |

## Example

Compute `acos(0.5)`, which is π/3 radians (60°).

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| acos(0.5) as angle_rad
```

**Expected output:**

| _timeslice | angle_rad |
|---|---|
| 2026-06-27 18:00:00 UTC | 1.0472 |
| 2026-06-27 19:00:00 UTC | 1.0472 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | acos(0.5) as angle_rad\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `acos(0.5)` = 1.0472 rad (π/3, 60°). `acos(1.0)` = 0. `acos(-1.0)` = 3.1416 (π).
- All FuseQL trigonometric operators work in radians. Multiply by `180 / 3.14159` to convert to degrees.
- Inputs outside `[-1, 1]` return `NaN`.
