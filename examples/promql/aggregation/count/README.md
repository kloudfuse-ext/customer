# count

Counts how many series the inner expression produced, per group. Useful for fleet-size questions: how many pods, how many targets.

## Syntax

```
count by (<labels>) (<expr>)    (also: count without (<labels>) (...))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keep only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Group by every label except the listed ones. |

## Example

Apply `count` to the goroutine gauges of the Kloudfuse query services, grouped by service name.

<!-- validation: kind=instant minutes=10 -->
```promql
count by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_name=~".*query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| rum-query-service | 116 |
| events-query-service | 195 |
| trace-query-service | 199 |
| query-service | 206 |
| logs-query-service | 200 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=count by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_name=~".*query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Without `by` or `without`, all labels are dropped and a single series is returned.
