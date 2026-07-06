# Range vector ([5m])

Appending a duration in square brackets to a selector returns a _range vector_: the raw samples of each series over that trailing window. Range vectors feed functions such as `rate`, `increase`, and the `*_over_time` family — they cannot be graphed directly.

## Syntax

```
<metric>{<matchers>}[<duration>]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<duration>` | Required | The window size: `30s`, `5m`, `1h`, `1d`. Use a window of at least 2–4× the metric's scrape interval so every step sees multiple samples. |

## Example

Average the query-service goroutine count over the samples of the last ten minutes.

<!-- validation: kind=instant minutes=10 -->
```promql
avg by (app_kubernetes_io_name) (avg_over_time(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| query-service | 329.59 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=avg by (app_kubernetes_io_name) (avg_over_time(go_goroutines{app_kubernetes_io_name="query-service"}[10m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- A range vector must be consumed by a function; `go_goroutines[5m]` alone is not a chartable expression.
