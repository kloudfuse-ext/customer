# Linear Forecast

Forecasts future metric values by fitting a linear regression model to historical time-series data. Use Linear Forecast when your data shows a consistent upward or downward trend without strong seasonal patterns.

## Syntax

```fuseql
| predict (<field>) by <bucket_size>, model=linear, forecast=<duration>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `(<field>)` | Required | The aggregated numeric field to forecast. |
| `by <bucket_size>` | Required | Time bucket size matching the upstream `timeslice` duration (e.g., `60s`, `5m`). |
| `model=linear` | Required | Selects the linear regression model. |
| `forecast=<duration>` | Required | How far forward to project, in seconds (e.g., `3600s` for 1 hour). |

## Example

Forecast nginx error counts 1 hour into the future using a linear model.

```fuseql
source="nginx"
| timeslice 60s
| count_unique(@error) by (_timeslice)
| predict (_count_unique) by 60s, model=linear, forecast=3600s
```

**Expected output (illustrative — last rows include forecasted values):**

| _timeslice | _count_unique | predicted |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 1,241 | — |
| 2026-06-27 19:00:00 UTC | — | 1,310 |
| 2026-06-27 19:30:00 UTC | — | 1,378 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 60s | count_unique(@error) by (_timeslice) | predict (_count_unique) by 60s, model=linear, forecast=3600s\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Linear forecasting works best for data with a clear monotonic trend.
- For data with cyclical (hourly/daily) patterns, use Seasonal Forecast instead.
- `forecast=3600s` projects 1 hour of additional data points beyond the last historical point.
