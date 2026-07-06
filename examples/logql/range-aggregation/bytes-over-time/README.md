# bytes_over_time

Sums the size in bytes of the log lines of each stream within the range window. Use it to see which sources, namespaces, or clusters generate log volume — the first question when managing ingest cost.

## Syntax

```
bytes_over_time({<selector>} [<pipeline>] [<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<selector>` | Required | Stream selector, optionally followed by a filter/parser pipeline. |
| `<range>` | Required | The window to sum over, such as `[5m]` or `[1h]`. |

## Example

Measure how many bytes of Kafka broker logs were produced in the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
sum(bytes_over_time({source="kafka"}[5m]))
```

**Expected output:**

| Value |
|---|
| 1,046,779 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(bytes_over_time({source="kafka"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- The value counts the raw line content, not labels or storage overhead.
