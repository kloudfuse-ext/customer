# sum

Adds the values of all input series into one series, or one series per group with `by (...)`. `sum` is the most common wrapper around a range aggregation — it collapses per-stream detail into totals along the dimension you care about.

## Syntax

```
sum by (<labels>) (<metric expression>)    (also: sum without (<labels>) (...))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keeps only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Groups by every label except the listed ones. |

## Example

Total Grafana's log volume per level over the last five minutes, collapsing all per-stream series into four rows.

<!-- validation: kind=instant minutes=10 -->
```logql
sum by (level) (count_over_time({source="grafana"}[5m]))
```

**Expected output:**

| level | Value |
|---|---|
| debug | 8,339 |
| error | 69,542 |
| info | 83,775 |
| warn | 10 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (level) (count_over_time({source="grafana"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Without `by` or `without`, all labels are dropped and a single series is returned.
