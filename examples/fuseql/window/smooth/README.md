# smooth

Applies a moving average (rolling mean) over a sliding window of rows. Use `smooth` to reduce noise in time-series data — for example, to flatten short-lived traffic spikes before charting.

## Syntax

```fuseql
| smooth(<field>) [, <window>] [as <alias>]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to smooth. |
| `<window>` | Optional | Number of rows in the sliding window. Defaults to `10`. |
| `as <alias>` | Optional | Output column name for the smoothed values. Defaults to `_smooth`. |

## Example

Apply a 3-row moving average to nginx request counts per minute.

```fuseql
source="nginx"
| timeslice 1m
| count by (_timeslice, source)
| smooth(_count, 3) as smoothed_requests
```

**Expected output:**

| _timeslice | source | _count | smoothed_requests |
|---|---|---|---|
| 2026-06-27 18:53:00 UTC | nginx | 61,441 | 61,441 |
| 2026-06-27 18:54:00 UTC | nginx | 650,712 | 356,077 |
| 2026-06-27 18:55:00 UTC | nginx | 474,040 | 395,397 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count by (_timeslice, source) | smooth(_count, 3) as smoothed_requests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `smooth` operates on time-ordered rows produced by a preceding `timeslice` stage.
- The first row of each group is returned unchanged (the window is not yet fully populated).
- Larger window sizes produce stronger smoothing but more lag before a true trend change is reflected.
