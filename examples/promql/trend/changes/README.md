# changes

Counts how many times each series changed value within the range window. Good for spotting flapping states and config churn.

## Syntax

```
changes(<gauge>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The trailing window to compute over. |

## Example

Count how often the query-service goroutine gauge changed value in ten minutes.

<!-- validation: kind=instant minutes=10 -->
```promql
max(changes(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))
```

**Expected output:**

| Value |
|---|
| 19 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=max(changes(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- A perfectly flat series returns 0; every scrape-to-scrape difference counts once.
