# ln

Applies `ln` to every sample value of the input vector, preserving all labels. Natural logarithm of every sample.

## Syntax

```
ln(<expr>)
```

## Example

Take the natural log of the Kloudfuse goroutine total — useful for charting values that span orders of magnitude.

<!-- validation: kind=instant minutes=10 -->
```promql
ln(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}))
```

**Expected output:**

| Value |
|---|
| 12.86 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=ln(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}))' \
  --data-urlencode "time=$(date -u +%s)"
```
