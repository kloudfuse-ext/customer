# count

Counts how many series the inner expression produced, per group when `by (...)` is given. Note the two levels of counting: `count_over_time` counts log lines within a stream, while `count` counts the resulting series — useful for questions like how many distinct streams are logging.

## Syntax

```
count by (<labels>) (<metric expression>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by (<labels>)` | Optional | Keeps only the listed labels as grouping dimensions. |
| `without (<labels>)` | Optional | Groups by every label except the listed ones. |

## Example

Count how many distinct log streams each source produced in the last five minutes — a quick way to see fleet size per component.

<!-- validation: kind=instant minutes=10 -->
```logql
count by (source) (count_over_time({source=~"zookeeper|kafka|busybox"}[5m]))
```

**Expected output:**

| source | Value |
|---|---|
| busybox | 34 |
| kafka | 176 |
| zookeeper | 109 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=count by (source) (count_over_time({source=~"zookeeper|kafka|busybox"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- A stream is a unique combination of all label values, so pods, hosts, and containers each contribute their own stream.
