# round

Rounds a number to the nearest integer using half-up rounding (0.5 rounds up). Use `round` to convert fractional averages or rates into clean integer values for display or downstream grouping.

## Syntax

```fuseql
| round(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute requests-per-second from per-minute counts, rounded to the nearest whole number.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| round(requests / 60) as rps
```

**Expected output:**

| _timeslice | requests | rps |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 1,024 |
| 2026-06-27 18:54:00 UTC | 650,712 | 10,845 |
| 2026-06-27 18:55:00 UTC | 474,040 | 7,901 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | round(requests / 60) as rps\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `round(3.5)` returns `4`; `round(3.4)` returns `3`.
- To always round up, use `ceil`. To always round down, use `floor`.
