# last_over_time

Returns the newest sample of each series within the range window — the right reader for sparsely reported gauges.

## Syntax

```
last_over_time(<metric>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to aggregate over. |

## Example

Apply `last_over_time` to the query-service goroutine gauge over the last ten minutes, then average across pods for a single row.

<!-- validation: kind=instant minutes=10 -->
```promql
avg by (app_kubernetes_io_name) (last_over_time(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| query-service | 313.16 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=avg by (app_kubernetes_io_name) (last_over_time(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Over-time functions aggregate one series across time; the aggregation operators (`sum`, `avg`, ...) aggregate across series at one instant. Combine both for fleet summaries.
