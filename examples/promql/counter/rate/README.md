# rate

Computes the per-second average rate of increase of a counter over the range window, handling counter resets. This is the default way to chart any `_total` metric and the basis of most alerts.

## Syntax

```
rate(<counter metric>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over, such as `[5m]`. |

## Example

Measure how fast the Kloudfuse ingester consumes Kafka batches.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(rate(ingester_kafka_batch_length_count[5m]))
```

**Expected output:**

| Value |
|---|
| 208,927.21 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(rate(ingester_kafka_batch_length_count[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Use a range of at least 2–4× the scrape interval; shorter windows see too few samples.
- For gauges, use `delta` or `deriv` — `rate` assumes counter semantics.
