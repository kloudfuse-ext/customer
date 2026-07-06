# deriv

Computes the per-second derivative of each series using simple linear regression over the range window — a smoothed answer to "which way is this gauge heading, and how fast".

## Syntax

```
deriv(<gauge>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over. |

## Example

Estimate the current growth rate of query-service goroutines.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(deriv(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))
```

**Expected output:**

| Value |
|---|
| 0.02797 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(deriv(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Regression smooths noise better than `delta / window`, at slightly more cost.
