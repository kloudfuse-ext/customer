# avg

Averages the values of the input series, per group when `by (...)` is given. Use it to compare typical per-stream levels across a dimension — for example, the average logging rate of each source.

## Syntax

```
avg by (<labels>) (<metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keeps only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Groups by every label except the listed ones. |

## Example

Compare the average per-stream logging rate of the ZooKeeper and Kafka clusters.

<!-- validation: kind=instant minutes=10 -->
```logql
avg by (source) (rate({source=~"zookeeper|kafka"}[5m]))
```

**Expected output:**

| source | Value |
|---|---|
| kafka | 0.09556 |
| zookeeper | 0.2436 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=avg by (source) (rate({source=~"zookeeper|kafka"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `avg` weighs every input series equally, regardless of how many lines each contributed.
