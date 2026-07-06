# increase

Computes how much a counter grew over the range window — `rate` multiplied by the window length. Human-friendly for questions like "how many requests in the last hour".

## Syntax

```
increase(<counter metric>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over, such as `[5m]`. |

## Example

Count Kafka batches the Kloudfuse ingester consumed in the last hour.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(increase(ingester_kafka_batch_length_count[1h]))
```

**Expected output:**

| Value |
|---|
| 209,835,585.76 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(increase(ingester_kafka_batch_length_count[1h]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- The result is extrapolated from samples, so it can be non-integer even for integer counters.
