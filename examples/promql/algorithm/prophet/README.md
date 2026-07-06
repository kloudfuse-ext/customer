# prophet

Kloudfuse extension. Fits Meta's Prophet model — additive trend plus multi-scale seasonality — to each series for forecasting and anomaly banding. See the Kloudfuse docs.

## Syntax

```
prophet(<expr>, <seasonality>, <bound>, <band>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<seasonality>` | Required | 0 = hourly, 1 = daily, 2 = weekly. |
| `<bound>` | Required | Band width in standard deviations: 1, 2, or 3. |
| `<band>` | Required | 4 = lower band, 5 = upper band, 6 = both. |

## Example

Band the query-service goroutine count with a Prophet model using daily seasonality at two standard deviations.

<!-- validation: kind=range_metric minutes=180 -->
```promql
prophet(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 1, 2, 6)
```

**Expected output:**

| result_type | Value |
|---|---|
| anomaly_both | 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=prophet(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 1, 2, 6)' \
  --data-urlencode "start=$(date -u -v-180M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "step=60"
```

## Notes

- Advance functions run in the Kloudfuse advanced-functions service, not in the PromQL engine, and fit a model per input series. Expect higher latency than standard functions, and aggregate first so the function receives few series — high-cardinality inputs degrade performance or time out.
