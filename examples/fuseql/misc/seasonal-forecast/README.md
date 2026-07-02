# Seasonal Forecast

Forecasts future metric values from time-series data with recurring seasonal patterns (hourly, daily cycles) and trends. Use Seasonal Forecast when your data shows predictable periodic behavior.

## Syntax

```fuseql
| predict (<field>) by <bucket_size>, model=seasonal, seasonality=<period>, forecast=<duration>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `(<field>)` | Required | The aggregated numeric field to forecast. |
| `by <bucket_size>` | Required | Time bucket size matching the upstream `timeslice` duration (e.g., `60s`, `5m`). |
| `model=seasonal` | Required | Selects the seasonal (Prophet) model. |
| `seasonality=<period>` | Required | The dominant seasonal period: `hourly` (24-hour cycle) or `daily` (7-day cycle). |
| `forecast=<duration>` | Required | How far forward to project, in seconds. |

## Example

Forecast nginx error counts 1 hour into the future using an hourly seasonal model.

```fuseql
source="nginx"
| timeslice 60s
| count_unique(@error) by (_timeslice)
| predict (_count_unique) by 60s, model=seasonal, seasonality=hourly, forecast=3600s
```

**Expected output (illustrative — last rows include forecasted values):**

| _timeslice | _count_unique | predicted |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 1,241 | — |
| 2026-06-27 19:00:00 UTC | — | 1,290 |
| 2026-06-27 19:30:00 UTC | — | 1,340 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 60s | count_unique(@error) by (_timeslice) | predict (_count_unique) by 60s, model=seasonal, seasonality=hourly, forecast=3600s\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Use `seasonality=hourly` for intra-day cycles (e.g., traffic spikes at the top of each hour).
- Use `seasonality=daily` for day-of-week patterns (e.g., higher traffic on weekdays).
- For data without seasonal patterns, use Linear Forecast instead.
