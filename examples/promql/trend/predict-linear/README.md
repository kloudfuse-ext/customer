# predict_linear

Predicts the value of each series `t` seconds from now by linear regression over the range window. The classic capacity alert: fire when disk will be full in four hours, not when it is full.

## Syntax

```
predict_linear(<gauge>[<range>], <seconds-ahead>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over. |

## Example

Project the query-service goroutine count one hour ahead based on the last 30 minutes.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(predict_linear(go_goroutines{app_kubernetes_io_name="query-service"}[30m], 3600))
```

**Expected output:**

| Value |
|---|
| 64,614.52 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(predict_linear(go_goroutines{app_kubernetes_io_name="query-service"}[30m], 3600))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Linear extrapolation only — for trends that curve, use the forecasting algorithms: the Kloudfuse docs.
