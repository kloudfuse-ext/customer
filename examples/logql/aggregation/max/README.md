# max

Returns the largest value among the input series, per group when `by (...)` is given. A common companion to `sum` on dashboards: the total tells you how much, the max tells you whether one member dominates.

## Syntax

```
max by (<labels>) (<metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keeps only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Groups by every label except the listed ones. |

## Example

Find the largest per-stream line count per log level for Grafana over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
max by (level) (count_over_time({source="grafana"}[5m]))
```

**Expected output:**

| level | Value |
|---|---|
| debug | 8,020 |
| error | 31,974 |
| info | 33,570 |
| warn | 4 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=max by (level) (count_over_time({source="grafana"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- To see which series holds the maximum, use `topk(1, ...)` — it keeps the series labels.
