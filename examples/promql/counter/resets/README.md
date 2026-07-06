# resets

Counts how many times a counter reset (dropped to a lower value) within the range window. Resets usually mean process restarts — a cheap restart detector from any counter you already collect.

## Syntax

```
resets(<counter metric>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over, such as `[5m]`. |

## Example

Check whether the ingester's Kafka counter reset in the last hour — zero means no restarts.

<!-- validation: kind=instant minutes=10 -->
```promql
max(resets(ingester_kafka_batch_length_count[1h]))
```

**Expected output:**

| Value |
|---|
| 2 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=max(resets(ingester_kafka_batch_length_count[1h]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Any decrease counts as a reset; gauges therefore produce meaningless results.
