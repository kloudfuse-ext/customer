# sort_desc

Sorts the input series by value in descending order — largest first. The natural choice for leaderboard-style panels where the biggest contributors should top the list.

## Syntax

```
sort_desc(<metric expression>)
```

## Example

List these sources' five-minute log volumes from loudest to quietest.

<!-- validation: kind=instant minutes=10 -->
```logql
sort_desc(sum by (source) (
  count_over_time({source=~"zookeeper|kafka|busybox"}[5m])
))
```

**Expected output:**

| source | Value |
|---|---|
| zookeeper | 9,298 |
| kafka | 5,758 |
| busybox | 371 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sort_desc(sum by (source) ( count_over_time({source=~"zookeeper|kafka|busybox"}[5m]) ))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- To limit the list as well as order it, use `topk` instead.
