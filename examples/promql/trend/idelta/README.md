# idelta

Computes the difference between the last two samples in the range window — the most recent movement of a gauge.

## Syntax

```
idelta(<gauge>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over. |

## Example

See the latest sample-to-sample change in query-service goroutines.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(idelta(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))
```

**Expected output:**

| Value |
|---|
| 35 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(idelta(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Like `irate`, `idelta` is volatile by design; use `delta` for smoother trends.
