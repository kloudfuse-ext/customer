# log10

Applies `log10` to every sample value of the input vector, preserving all labels. Base-10 logarithm of every sample.

## Syntax

```
log10(<expr>)
```

## Example

Find the order of magnitude of the Kloudfuse goroutine total.

<!-- validation: kind=instant minutes=10 -->
```promql
log10(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}))
```

**Expected output:**

| Value |
|---|
| 5.585 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=log10(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}))' \
  --data-urlencode "time=$(date -u +%s)"
```
