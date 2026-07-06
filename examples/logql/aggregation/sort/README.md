# sort

Sorts the input series by value in ascending order. Sorting affects presentation only — the series and values are unchanged — and applies to instant queries, where results are a flat list.

## Syntax

```
sort(<metric expression>)
```

## Example

List these sources' five-minute log volumes from quietest to loudest.

<!-- validation: kind=instant minutes=10 -->
```logql
sort(sum by (source) (
  count_over_time({source=~"zookeeper|kafka|busybox"}[5m])
))
```

**Expected output:**

| source | Value |
|---|---|
| busybox | 356 |
| kafka | 5,635 |
| zookeeper | 8,973 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sort(sum by (source) ( count_over_time({source=~"zookeeper|kafka|busybox"}[5m]) ))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Use `sort_desc` for descending order.
