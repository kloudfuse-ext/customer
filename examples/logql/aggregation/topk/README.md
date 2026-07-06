# topk

Returns the `k` input series with the largest values, keeping their labels. `topk` answers ranking questions directly — the noisiest sources, the busiest namespaces — without pulling the full series list.

## Syntax

```
topk(<k>, <metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<k>` | Required | How many series to return. |

## Example

Rank the three chattiest of these five sources by log volume over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
topk(3, sum by (source) (
  count_over_time({source=~"zookeeper|kafka|busybox|filebeat|catalog-service"}[5m])
))
```

**Expected output:**

| source | Value |
|---|---|
| busybox | 327 |
| kafka | 5,340 |
| zookeeper | 8,352 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=topk(3, sum by (source) ( count_over_time({source=~"zookeeper|kafka|busybox|filebeat|catalog-service"}[5m]) ))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- In range queries `topk` is evaluated at every step, so the membership of the top set can change over time.
