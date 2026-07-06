# min

Returns the smallest value among the input series per group — the floor of a fleet.

## Syntax

```
min by (<labels>) (<expr>)    (also: min without (<labels>) (...))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keep only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Group by every label except the listed ones. |

## Example

Apply `min` to the goroutine gauges of the Kloudfuse query services, grouped by service name.

<!-- validation: kind=instant minutes=10 -->
```promql
min by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_name=~".*query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| trace-query-service | 12 |
| query-service | 13 |
| rum-query-service | 9 |
| events-query-service | 12 |
| logs-query-service | 10 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=min by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_name=~".*query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Without `by` or `without`, all labels are dropped and a single series is returned.
