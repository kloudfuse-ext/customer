# accum

Computes the cumulative running sum of a numeric field across time-ordered rows. Each output row contains the sum of the current and all preceding rows' values. Use `accum` to build running totals — for example, cumulative request counts over a session window.

## Syntax

```fuseql
| accum(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to accumulate. |
| `as <alias>` | Optional | Output column name for the running sum. Defaults to `_accum`. |
| `by <field1>, ...` | Optional | Groups accumulation by one or more fields, restarting the running sum for each group. |

## Example

Count nginx requests per 1-minute bucket, then compute a cumulative running total.

```fuseql
source="nginx"
| timeslice 1m
| count by (_timeslice, source)
| accum(_count) as cumulative_requests
```

**Expected output:**

| _timeslice | source | _count | cumulative_requests |
|---|---|---|---|
| 2026-06-27 18:53:00 UTC | nginx | 61,441 | 61,441 |
| 2026-06-27 18:54:00 UTC | nginx | 650,712 | 712,153 |
| 2026-06-27 18:55:00 UTC | nginx | 474,040 | 1,186,193 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count by (_timeslice, source) | accum(_count) as cumulative_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `accum` operates on time-ordered rows produced by a preceding `timeslice` stage.
- When using `by`, each unique combination of group values maintains an independent running sum.
- To add the grand total (not the running sum) to every row, use `total` instead.
