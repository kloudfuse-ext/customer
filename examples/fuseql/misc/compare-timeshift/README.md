# compare timeshift

Adds one or more columns containing time-shifted historical values alongside current aggregated data. Use it to perform day-over-day, week-over-week, or custom-period comparisons in a single query.

## Syntax

```fuseql
| compare timeshift <duration>
| compare timeshift <duration> <count>
| compare timeshift <duration> as <alias>
| compare timeshift <duration> as <alias>, timeshift <duration2> as <alias2>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<duration>` | Required | How far back to shift. Units: `m`, `h`, `d`, `w`. |
| `<count>` | Optional | Number of shifted periods to generate. Creates `<count>` columns. Default: `1`. |
| `as <alias>` | Optional | Custom name for the comparison column. Without alias, columns are named `<metric>_<duration>_<index>`. |

## Example

Compare hourly nginx request counts with yesterday and last week.

```fuseql
source="nginx"
| timeslice 1h
| count by (_timeslice)
| compare timeshift 1d as yesterday, timeshift 1w as last_week
```

**Expected output (illustrative):**

| _timeslice | _count | count_yesterday | count_last_week |
|---|---|---|---|
| 2026-06-27 18:00:00 UTC | 650,712 | 598,240 | 612,450 |
| 2026-06-27 19:00:00 UTC | 474,040 | 441,800 | 488,920 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count by (_timeslice) | compare timeshift 1d as yesterday, timeshift 1w as last_week\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `compare timeshift` can only be used after an aggregation operator.
- Shifted columns return `NULL` when no matching historical data exists.
- Column naming: with alias → `<metric>_<alias>`; without alias → `<metric>_<duration>_<index>`.
