# Combining filters (and, or)

Combines multiple label filter predicates in one expression. `and` requires both sides to hold — a comma or a space between predicates means the same thing — while `or` matches when either side holds. Use parentheses to group nested conditions.

## Syntax

```
| <predicate> and <predicate> [or <predicate>]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<predicate>` | Required | Any label filter comparison: string, numeric, duration, or bytes. |

## Example

Keep Grafana datasource requests that were both slow (over 5 ms) and successful (status 200).

<!-- validation: kind=range minutes=10 -->
```logql
{source="grafana"} |= "duration="
| logfmt
| duration > 5ms and statusCode="200"
```

**Expected output:**

```
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseLogsDatasource dsUID=P10239062BE9ED4EF uname=gra ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseLogsDatasource dsUID=P10239062BE9ED4EF uname=gra ...
logger=tsdb.loki endpoint=queryData pluginId=loki dsName=KfuseLogsDatasource dsUID=P10239062BE9ED4EF uname=gra ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="grafana"} |= "duration=" | logfmt | duration > 5ms and statusCode="200"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- `| duration > 5ms, statusCode="200"` and `| duration > 5ms | statusCode="200"` are equivalent ways to write the same `and`.
