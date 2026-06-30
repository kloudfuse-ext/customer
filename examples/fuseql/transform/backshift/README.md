# backshift

Returns the value of a numeric field from N rows back in a time-ordered result set. Use `backshift` to compute period-over-period deltas by subtracting the shifted value from the current value.

## Syntax

```fuseql
| backshift <field> [, <n>] [as <alias>]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field whose previous-row value is retrieved. |
| `<n>` | Optional | Number of rows to shift back. Defaults to `1`. |
| `as <alias>` | Optional | Output column name for the shifted value. Defaults to `_backshift`. |

## Example

Compute per-minute request deltas by shifting the count back by 1 row.

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| backshift requests, 1 as prev_requests
| (requests - prev_requests) as delta
```

**Expected output:**

| _timeslice | requests | prev_requests | delta |
|---|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | (null) | (null) |
| 2026-06-27 18:54:00 UTC | 650,712 | 61,441 | 589,271 |
| 2026-06-27 18:55:00 UTC | 474,040 | 650,712 | -176,672 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | backshift requests, 1 as prev_requests | (requests - prev_requests) as delta\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- The first row always returns null for the shifted field (no preceding row exists).
- `backshift` operates on time-ordered rows from a preceding `timeslice` stage.
- Combine with `smooth` to reduce noise in the delta series.
