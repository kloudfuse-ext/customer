# avg

Averages the values of the input series per group. Every series weighs equally regardless of how it was produced.

## Syntax

```
avg by (<labels>) (<expr>)    (also: avg without (<labels>) (...))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keep only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Group by every label except the listed ones. |

## Example

Apply `avg` to the goroutine gauges of the Kloudfuse query services, grouped by service name.

<!-- validation: kind=instant minutes=10 -->
```promql
avg by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_name=~".*query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| trace-query-service | 15.42 |
| logs-query-service | 97.5 |
| rum-query-service | 11.34 |
| events-query-service | 15.5 |
| query-service | 313.35 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=avg by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_name=~".*query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Without `by` or `without`, all labels are dropped and a single series is returned.
