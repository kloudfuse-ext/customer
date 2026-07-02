# tan

Returns the tangent of a number given in radians. Undefined at multiples of π/2 (where the function diverges to ±infinity).

## Syntax

```fuseql
| tan(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value, interpreted as radians. Avoid values near π/2 multiples. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute `tan(0)` = 0.0 and `tan(π/4)` = 1.0.

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| tan(0) as tan_0, tan(0.7854) as tan_45deg
```

**Expected output:**

| _timeslice | tan_0 | tan_45deg |
|---|---|---|
| 2026-06-27 18:00:00 UTC | 0.0 | 1.0 |
| 2026-06-27 19:00:00 UTC | 0.0 | 1.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | tan(0) as tan_0, tan(0.7854) as tan_45deg\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `tan(0)` = 0.0. `tan(0.7854)` = 1.0 (π/4, 45°).
- The function diverges near π/2 (~1.5708 rad). Avoid inputs very close to this value.
