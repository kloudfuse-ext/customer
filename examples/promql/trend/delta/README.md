# delta

Computes the difference between the first and last value of each series in the range window, extrapolated to the window ends. The gauge counterpart of `increase`: how much did this value move.

## Syntax

```
delta(<gauge>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over. |

## Example

Measure how much the query-service goroutine count changed over the last 30 minutes.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))
```

**Expected output:**

| Value |
|---|
| 34.06 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(delta(go_goroutines{app_kubernetes_io_name="query-service"}[30m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- For counters use `increase`, which handles resets.
