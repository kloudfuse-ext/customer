# seasonal_forecast

Kloudfuse extension. Projects each series into the future using its seasonal history — the seasonal counterpart of `predict_linear` for trends that repeat rather than run straight.

## Syntax

```
seasonal_forecast(<expr>, <seasonality>, <result>, <duration>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<seasonality>` | Required | 0 = hourly, 1 = daily, 2 = weekly. |
| `<result>` | Required | 0 = forecast, 1 = upper band, 2 = lower band, 3 = all. |
| `<duration>` | Required | Forecast duration in timestamps. |

## Example

Forecast the query-service goroutine count an hour ahead using daily seasonality.

<!-- validation: kind=range_metric minutes=180 -->
```promql
seasonal_forecast(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 1, 0, 60)
```

**Expected output:**

| result_type | Value |
|---|---|
| mean | 65,133.97 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=seasonal_forecast(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 1, 0, 60)' \
  --data-urlencode "start=$(date -u -v-180M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "step=60"
```

## Notes

- Advance functions run in the Kloudfuse advanced-functions service, not in the PromQL engine, and fit a model per input series. Expect higher latency than standard functions, and aggregate first so the function receives few series — high-cardinality inputs degrade performance or time out.
