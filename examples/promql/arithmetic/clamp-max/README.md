# clamp_max

Applies `clamp_max` to every sample value of the input vector, preserving all labels. Limits every sample to a maximum.

## Syntax

```
clamp_max(<expr>, <max>)
```

## Example

Cap the Kloudfuse goroutine total at 10,000.

<!-- validation: kind=instant minutes=10 -->
```promql
clamp_max(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}), 10000)
```

**Expected output:**

| Value |
|---|
| 10,000 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=clamp_max(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}), 10000)' \
  --data-urlencode "time=$(date -u +%s)"
```
