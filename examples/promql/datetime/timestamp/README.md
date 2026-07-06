# timestamp

Replaces every sample's value with that sample's timestamp in Unix seconds, preserving labels. Combined with `time()`, it measures data freshness: how old is the newest sample of each series.

## Syntax

```
timestamp(<expr>)
```

## Example

Measure the age in seconds of the newest query-service goroutine sample — small values mean fresh data.

<!-- validation: kind=instant minutes=10 -->
```promql
time() - max(timestamp(go_goroutines{app_kubernetes_io_name="query-service"}))
```

**Expected output:**

| Value |
|---|
| 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=time() - max(timestamp(go_goroutines{app_kubernetes_io_name="query-service"}))' \
  --data-urlencode "time=$(date -u +%s)"
```
