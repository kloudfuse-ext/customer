# total

Adds the grand total of a numeric field across all rows as an additional column. Unlike aggregation operators that reduce the row count, `total` preserves every row. Use it to compute each time bucket's share of overall traffic.

## Syntax

```fuseql
| total(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to sum across all rows. |
| `as <alias>` | Optional | Output column name for the total. Defaults to `_total`. |
| `by <field1>, ...` | Optional | Groups the total computation independently per group. |

## Example

Append the grand total of nginx requests and compute each bucket's percentage share.

```fuseql
source="nginx"
| timeslice 1m
| count by (_timeslice, source)
| total(_count) as total_requests
| (_count / total_requests) * 100 as pct_of_total
```

**Expected output:**

| _timeslice | _count | total_requests | pct_of_total |
|---|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 1,868,307 | 3.29 |
| 2026-06-27 18:54:00 UTC | 650,712 | 1,868,307 | 34.83 |
| 2026-06-27 18:55:00 UTC | 474,040 | 1,868,307 | 25.37 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count by (_timeslice, source) | total(_count) as total_requests | (_count / total_requests) * 100 as pct_of_total\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `total` adds the same fixed grand total to every row — unlike `accum`, which produces a running sum.
- Use `by` to compute totals per group rather than across all rows.
