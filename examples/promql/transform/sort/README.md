# sort

Orders the series of an instant query by value, smallest first. Sorting affects presentation only — labels and values are unchanged — and applies to instant queries, where the result is a flat list.

## Syntax

```
sort(<expr>)
```

## Example

List Kloudfuse query services from fewest to most goroutines.

<!-- validation: kind=instant minutes=10 -->
```promql
sort(sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"}))
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| rum-query-service | 1,319 |
| events-query-service | 3,019 |
| trace-query-service | 3,057 |
| logs-query-service | 19,524 |
| query-service | 64,559 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sort(sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"}))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- To limit as well as order, use `topk`/`bottomk`.
