# rollingstd

Computes the rolling standard deviation of a numeric field over a sliding window of rows. A sudden increase in rolling standard deviation can indicate instability or an anomalous traffic pattern.

## Syntax

```fuseql
| rollingstd(<field>) [, <window>] [as <alias>]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field over which to compute the rolling standard deviation. |
| `<window>` | Optional | Number of rows in the sliding window. Defaults to `10`. |
| `as <alias>` | Optional | Output column name. Defaults to `_rollingstd`. |

## Example

Compute rolling standard deviation of nginx request counts over a 3-row window to identify volatile time periods.

```fuseql
source="nginx"
| timeslice 1m
| count by (_timeslice, source)
| rollingstd(_count, 3) as rolling_stddev
```

**Expected output:**

| _timeslice | source | _count | rolling_stddev |
|---|---|---|---|
| 2026-06-27 18:53:00 UTC | nginx | 61,441 | 0 |
| 2026-06-27 18:54:00 UTC | nginx | 650,712 | 294,636 |
| 2026-06-27 18:55:00 UTC | nginx | 474,040 | 244,984 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count by (_timeslice, source) | rollingstd(_count, 3) as rolling_stddev\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `rollingstd` operates on time-ordered rows from a preceding `timeslice` stage.
- The first row in each group returns `0` (only one data point — standard deviation is undefined).
- Pair with `smooth` to compare the moving average against the rolling variability band.
