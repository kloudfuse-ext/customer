# irate

Computes the per-second rate using only the last two samples in the range window. `irate` reacts instantly to change, at the cost of volatility — suited to zoomed-in debugging graphs, not alerts.

## Syntax

```
irate(<counter metric>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over, such as `[5m]`. |

## Example

See the instantaneous Kafka batch consumption rate of the ingester.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(irate(ingester_kafka_batch_length_count[5m]))
```

**Expected output:**

| Value |
|---|
| 492,814.12 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(irate(ingester_kafka_batch_length_count[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Alerts on `irate` flap; prefer `rate` for anything automated.
