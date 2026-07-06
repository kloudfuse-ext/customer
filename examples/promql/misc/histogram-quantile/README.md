# histogram_quantile

Estimates the given quantile (0 to 1) from the `_bucket` series of a Prometheus histogram. The canonical form wraps the buckets in `sum by (le) (rate(...))` so the estimate reflects recent behavior and the mandatory `le` label survives the aggregation.

## Syntax

```
histogram_quantile(<q>, sum by (le) (rate(<metric>_bucket[<range>])))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<q>` | Required | The quantile, between 0 and 1. |
| `<metric>_bucket` | Required | Histogram bucket series carrying the `le` label. |

## Example

Estimate the 95th-percentile Kafka batch length seen by the Kloudfuse ingester over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```promql
histogram_quantile(0.95,
  sum by (le) (rate(ingester_kafka_batch_length_bucket[5m]))
)
```

**Expected output:**

| Value |
|---|
| 37.09 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=histogram_quantile(0.95, sum by (le) (rate(ingester_kafka_batch_length_bucket[5m])) )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- The result is interpolated within a bucket, so precision depends on bucket boundaries.
- Any aggregation around the buckets must keep the `le` label.
