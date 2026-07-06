# kf_rolling_quantile

Kloudfuse extension. Computes a rolling quantile band over each series and flags samples that fall outside it — a robust, assumption-free anomaly detector. See the Kloudfuse docs.

## Syntax

```
kf_rolling_quantile(<expr>, <window>, <bound>, <band>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<window>` | Required | Rolling window in milliseconds — 1800000 for a 30-minute window. |
| `<bound>` | Required | Band width in standard deviations: 1, 2, or 3. |
| `<band>` | Required | 4 = lower band, 5 = upper band, 6 = both; 0–3 return the raw prediction series instead (0 predictions, 1 lower, 2 upper, 3 all). |

## Example

Band the query-service goroutine count with a 30-minute rolling quantile at two standard deviations, returning both bands.

<!-- validation: kind=range_metric minutes=180 -->
```promql
kf_rolling_quantile(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 1800000, 2, 6)
```

**Expected output:**

| result_type | Value |
|---|---|
| anomaly_both | 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=kf_rolling_quantile(sum(go_goroutines{app_kubernetes_io_name="query-service"}), 1800000, 2, 6)' \
  --data-urlencode "start=$(date -u -v-180M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "step=60"
```

## Notes

- Advance functions run in the Kloudfuse advanced-functions service, not in the PromQL engine, and fit a model per input series. Expect higher latency than standard functions, and aggregate first so the function receives few series — high-cardinality inputs degrade performance or time out.
