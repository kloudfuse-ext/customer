# round

Applies `round` to every sample value of the input vector, preserving all labels. Rounds every sample to the nearest multiple.

## Syntax

```
round(<expr> [, <to-nearest>])
```

## Example

Round the Kloudfuse goroutine total to the nearest hundred.

<!-- validation: kind=instant minutes=10 -->
```promql
round(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}), 100)
```

**Expected output:**

| Value |
|---|
| 385,100 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=round(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}), 100)' \
  --data-urlencode "time=$(date -u +%s)"
```
