# group

Collapses each group to a single series with value 1. Use it to deduplicate label combinations before counting or joining, when the values themselves do not matter.

## Syntax

```
group by (<labels>) (<expr>)    (also: group without (<labels>) (...))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keep only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Group by every label except the listed ones. |

## Example

Apply `group` to the goroutine gauges of the Kloudfuse query services, grouped by service name.

<!-- validation: kind=instant minutes=10 -->
```promql
group by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_name=~".*query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| logs-query-service | 1 |
| rum-query-service | 1 |
| events-query-service | 1 |
| query-service | 1 |
| trace-query-service | 1 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=group by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_name=~".*query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Without `by` or `without`, all labels are dropped and a single series is returned.
