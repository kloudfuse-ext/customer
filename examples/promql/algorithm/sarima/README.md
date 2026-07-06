# sarima

Kloudfuse extension. Fits a Seasonal Autoregressive Integrated Moving Average model to each series and returns the predicted band, flagging values that escape it. The strongest choice for metrics with clear seasonality. See the Kloudfuse docs for the model parameters in depth.

## Syntax

```
sarima(<expr>, <p>, <d>, <q>, <sp>, <sd>, <sq>, <sm>, <bound>, <band>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<p>, <d>, <q>` | Required | Autoregression order, differencing order, and moving-average order. |
| `<sp>, <sd>, <sq>, <sm>` | Required | Seasonal counterparts plus the number of timestamps per season. |
| `<bound>` | Required | Band width in standard deviations: 1, 2, or 3. |
| `<band>` | Required | 4 = lower band, 5 = upper band, 6 = both. |

## Example

Band the query-service goroutine count with a non-seasonal ARIMA model at two standard deviations, returning both bands.

<!-- validation: kind=range_metric minutes=180 -->
```promql
sarima(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 2, 1, 2, 0, 0, 0, 0, 2, 6)
```

**Expected output:**

| result_type | Value |
|---|---|
| anomaly_both | 1 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sarima(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 2, 1, 2, 0, 0, 0, 0, 2, 6)' \
  --data-urlencode "start=$(date -u -v-180M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "step=60"
```

## Notes

- Advance functions run in the Kloudfuse advanced-functions service, not in the PromQL engine, and fit a model per input series. Expect higher latency than standard functions, and aggregate first so the function receives few series — high-cardinality inputs degrade performance or time out.
