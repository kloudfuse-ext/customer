# abs

Applies `abs` to every sample value of the input vector, preserving all labels. Absolute value of every sample.

## Syntax

```
abs(<expr>)
```

## Example

Measure how far the query-service goroutine count moved in 30 minutes, regardless of direction.

<!-- validation: kind=instant minutes=10 -->
```promql
abs(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))
```

**Expected output:**

| Value |
|---|
| 1.678 |
| 1.119 |
| 0 |
| 0.3051 |
| 0.6102 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=abs(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))' \
  --data-urlencode "time=$(date -u +%s)"
```
