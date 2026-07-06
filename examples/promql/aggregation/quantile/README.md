# quantile

Computes the given quantile (0 to 1) across the values of the input series, per group. This is a cross-series statistic at one instant — for a quantile of one series over time, use `quantile_over_time`; for histogram data, use `histogram_quantile`.

## Syntax

```
quantile(<q>, <expr>)    (also: quantile by (<labels>) (<q>, ...))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<q>` | Required | The quantile, between 0 and 1. |

## Example

Find the 90th-percentile per-series goroutine count across all Kloudfuse service pods.

<!-- validation: kind=instant minutes=10 -->
```promql
quantile(0.9, go_goroutines{app_kubernetes_io_instance="kfuse"})
```

**Expected output:**

| Value |
|---|
| 375 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=quantile(0.9, go_goroutines{app_kubernetes_io_instance="kfuse"})' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Three quantile tools, three scopes: `quantile` across series, `quantile_over_time` across time, `histogram_quantile` across histogram buckets.
