# stddev

Computes the population standard deviation of the input series values, per group when `by (...)` is given. Use it to quantify imbalance across a fleet — a high deviation in per-stream log counts means a few members are much noisier than the rest.

## Syntax

```
stddev by (<labels>) (<metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keeps only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Groups by every label except the listed ones. |

## Example

Measure how unevenly log volume is distributed across Grafana's streams in the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
stddev(count_over_time({source="grafana"}[5m]))
```

**Expected output:**

| Value |
|---|
| 3,591.81 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=stddev(count_over_time({source="grafana"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- This aggregates across series at one instant; `stddev_over_time` aggregates one stream's samples across time.
