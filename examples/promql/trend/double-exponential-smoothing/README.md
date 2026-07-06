# double_exponential_smoothing

Smooths each series using double exponential (Holt-Winters) smoothing: `sf` weighs recent samples, `tf` weighs recent trend. Produces a stable signal from a noisy gauge.

## Syntax

```
double_exponential_smoothing(<gauge>[<range>], <sf>, <tf>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over. |

## Example

Smooth the query-service goroutine gauge with balanced smoothing and trend factors.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(double_exponential_smoothing(go_goroutines{app_kubernetes_io_name="query-service"}[30m], 0.5, 0.5))
```

**Expected output:**

| Value |
|---|
| 64,783.09 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(double_exponential_smoothing(go_goroutines{app_kubernetes_io_name="query-service"}[30m], 0.5, 0.5))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Both factors are between 0 and 1: lower `sf` smooths harder, higher `tf` follows trend changes faster.
- This function was named `holt_winters` in Prometheus 2.x; Kloudfuse uses the current name.
