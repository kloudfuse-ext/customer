# sgn

Applies `sgn` to every sample value of the input vector, preserving all labels. Sign of every sample: -1, 0, or 1.

## Syntax

```
sgn(<expr>)
```

## Example

Reduce the 30-minute goroutine trend to its direction: growing (1), flat (0), or shrinking (-1).

<!-- validation: kind=instant minutes=10 -->
```promql
sgn(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))
```

**Expected output:**

| Value |
|---|
| -1 |
| 1 |
| 1 |
| -1 |
| -1 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sgn(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))' \
  --data-urlencode "time=$(date -u +%s)"
```
