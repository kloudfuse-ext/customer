# floor

Applies `floor` to every sample value of the input vector, preserving all labels. Rounds every sample down to the nearest integer.

## Syntax

```
floor(<expr>)
```

## Example

Round the Kloudfuse goroutine total down to the previous thousand.

<!-- validation: kind=instant minutes=10 -->
```promql
floor(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}) / 1000)
```

**Expected output:**

| Value |
|---|
| 385 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=floor(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}) / 1000)' \
  --data-urlencode "time=$(date -u +%s)"
```
