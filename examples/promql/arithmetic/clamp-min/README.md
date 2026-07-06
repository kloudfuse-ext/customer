# clamp_min

Applies `clamp_min` to every sample value of the input vector, preserving all labels. Limits every sample to a minimum.

## Syntax

```
clamp_min(<expr>, <min>)
```

## Example

Treat any decrease in goroutines as zero, keeping only growth.

<!-- validation: kind=instant minutes=10 -->
```promql
clamp_min(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]), 0)
```

**Expected output:**

| Value |
|---|
| 0.5085 |
| 0 |
| 0 |
| 0.05085 |
| 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=clamp_min(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]), 0)' \
  --data-urlencode "time=$(date -u +%s)"
```
