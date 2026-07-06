# seasonal_decompose

Kloudfuse extension. Splits each series into trend, seasonal, and residual components and flags points whose residual is anomalous. See the Kloudfuse docs for the full treatment.

## Syntax

```
seasonal_decompose(<expr>, <period>, <model>, <window>, <bound>, <band>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<period>` | Required | Data points per season — 1440 at 1-minute resolution for daily seasonality. |
| `<model>` | Required | 0 = additive decomposition, 1 = multiplicative. |
| `<window>` | Required | Smoothing window in milliseconds — 1800000 for 30 minutes. |
| `<bound>` | Required | Band width in standard deviations: 1, 2, or 3. |
| `<band>` | Required | 4 = lower band, 5 = upper band, 6 = both. |

## Example

Decompose the query-service goroutine count with a one-hour season and additive model, returning both anomaly bands.

<!-- validation: kind=range_metric minutes=180 -->
```promql
seasonal_decompose(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 60, 0, 1800000, 2, 6)
```

**Expected output:**

| result_type | Value |
|---|---|
| anomaly_both | 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=seasonal_decompose(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 60, 0, 1800000, 2, 6)' \
  --data-urlencode "start=$(date -u -v-180M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "step=60"
```

## Notes

- Advance functions run in the Kloudfuse advanced-functions service, not in the PromQL engine, and fit a model per input series. Expect higher latency than standard functions, and aggregate first so the function receives few series — high-cardinality inputs degrade performance or time out.
