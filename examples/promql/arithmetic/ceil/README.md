# ceil

Applies `ceil` to every sample value of the input vector, preserving all labels. Rounds every sample up to the nearest integer.

## Syntax

```
ceil(<expr>)
```

## Example

Round the Kloudfuse goroutine total up to the next thousand.

<!-- validation: kind=instant minutes=10 -->
```promql
ceil(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}) / 1000)
```

**Expected output:**

| Value |
|---|
| 386 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=ceil(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}) / 1000)' \
  --data-urlencode "time=$(date -u +%s)"
```
