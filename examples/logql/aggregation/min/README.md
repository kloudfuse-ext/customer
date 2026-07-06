# min

Returns the smallest value among the input series, per group when `by (...)` is given. Use it to find the quietest member of a fleet or the lower bound of a metric across streams.

## Syntax

```
min by (<labels>) (<metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keeps only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Groups by every label except the listed ones. |

## Example

Find the lowest per-stream line count among all Grafana streams in the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
min(count_over_time({source="grafana"}[5m]))
```

**Expected output:**

| Value |
|---|
| 1 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=min(count_over_time({source="grafana"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `min`/`max` pick one value per group; to rank several series use `bottomk`/`topk`.
