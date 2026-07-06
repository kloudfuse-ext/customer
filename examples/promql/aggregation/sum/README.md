# sum

Adds up the values of all input series, per group when `by (...)` is given. The most common aggregation: totals along the dimension you care about, per-stream detail collapsed.

## Syntax

```
sum by (<labels>) (<expr>)    (also: sum without (<labels>) (...))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keep only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Group by every label except the listed ones. |

## Example

Apply `sum` to the goroutine gauges of the Kloudfuse query services, grouped by service name.

<!-- validation: kind=instant minutes=10 -->
```promql
sum by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_name=~".*query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| rum-query-service | 1,317 |
| query-service | 64,560 |
| trace-query-service | 3,066 |
| logs-query-service | 19,501 |
| events-query-service | 3,022 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_name=~".*query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Without `by` or `without`, all labels are dropped and a single series is returned.
