# ceil

Rounds a number up to the nearest integer (ceiling function). Use `ceil` to ensure values never fall below a threshold when converting fractional counts or rates to discrete integers.

## Syntax

```fuseql
| ceil(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Express nginx requests-per-second rounded up to the nearest whole number.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| ceil(requests / 60) as ceil_rps
```

**Expected output:**

| _timeslice | requests | ceil_rps |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 1,024 |
| 2026-06-27 18:54:00 UTC | 650,712 | 10,846 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | ceil(requests / 60) as ceil_rps\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `ceil(3.14)` returns `4`. Even `ceil(3.001)` returns `4`.
- For rounding toward zero (down for positive numbers), use `floor`.
- For rounding to the nearest integer (half-up), use `round`.
