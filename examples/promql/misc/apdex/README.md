# apdex

Kloudfuse extension. Computes the Apdex score — (satisfied + tolerated/2) / total — from histogram bucket series, using the two thresholds to classify requests as satisfied (≤ first threshold) or tolerated (≤ second threshold). The score ranges from 0 (all frustrated) to 1 (all satisfied).

## Syntax

```
apdex(<satisfied>, <tolerated>, sum by (le) (rate(<metric>_bucket[<range>])))
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<satisfied>` | Required | Threshold at or below which a request counts as satisfied. |
| `<tolerated>` | Required | Threshold at or below which a request counts as tolerated. |
| `<metric>_bucket` | Required | Histogram bucket series carrying the `le` label. |

## Example

Score the Kloudfuse ingester's Kafka batch sizes with satisfied ≤ 10 and tolerated ≤ 40.

<!-- validation: kind=instant minutes=10 -->
```promql
apdex(10, 40,
  sum by (le) (rate(ingester_kafka_batch_length_bucket[5m]))
)
```

**Expected output:**

| Value |
|---|
| 0.8824 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=apdex(10, 40, sum by (le) (rate(ingester_kafka_batch_length_bucket[5m])) )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Thresholds must align with actual bucket boundaries for exact classification; between boundaries the count is interpolated.
- `apdex` is a Kloudfuse extension and is not available in upstream Prometheus.
