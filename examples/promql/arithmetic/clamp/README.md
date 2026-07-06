# clamp

Applies `clamp` to every sample value of the input vector, preserving all labels. Limits every sample to a min–max range.

## Syntax

```
clamp(<expr>, <min>, <max>)
```

## Example

Cap the Kloudfuse goroutine total at 10,000 and floor it at 0 — outliers no longer stretch the chart axis.

<!-- validation: kind=instant minutes=10 -->
```promql
clamp(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}), 0, 10000)
```

**Expected output:**

| Value |
|---|
| 10,000 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=clamp(sum(go_goroutines{app_kubernetes_io_instance="kfuse"}), 0, 10000)' \
  --data-urlencode "time=$(date -u +%s)"
```
