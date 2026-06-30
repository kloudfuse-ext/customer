# asin

Returns the arcsine (inverse sine) of a number, in radians. The input must be in the range `[-1, 1]`.

## Syntax

```fuseql
| asin(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal in the range `[-1, 1]`. Values outside this range return `NaN`. |
| `as <alias>` | Required | Output column name for the result, in radians. |

## Example

Compute `asin(0.5)`, which is π/6 radians (30°).

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| asin(0.5) as angle_rad
```

**Expected output:**

| _timeslice | angle_rad |
|---|---|
| 2026-06-27 18:00:00 UTC | 0.5236 |
| 2026-06-27 19:00:00 UTC | 0.5236 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | asin(0.5) as angle_rad\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `asin(0.5)` = 0.5236 rad (π/6, 30°). `asin(0)` = 0. `asin(1)` = 1.5708 (π/2, 90°).
- All FuseQL trigonometric operators work in radians.
- Inputs outside `[-1, 1]` return `NaN`.
