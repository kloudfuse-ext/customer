# sort_desc

Orders the series of an instant query by value, largest first — the natural order for leaderboard-style panels.

## Syntax

```
sort_desc(<expr>)
```

## Example

List Kloudfuse query services from most to fewest goroutines.

<!-- validation: kind=instant minutes=10 -->
```promql
sort_desc(sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"}))
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| query-service | 64,589 |
| logs-query-service | 19,522 |
| trace-query-service | 3,060 |
| events-query-service | 3,018 |
| rum-query-service | 1,315 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sort_desc(sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"}))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- In range queries, sorting has no effect — each step is evaluated independently.
