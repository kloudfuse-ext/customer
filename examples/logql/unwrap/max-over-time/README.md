# max_over_time

Returns the largest unwrapped value within the range window. This is the worst-case detector: slowest request, biggest payload, highest queue depth — often more actionable than the average.

## Syntax

```
max_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to take the maximum over. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Find the slowest Grafana datasource request per endpoint in the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
max_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 31.88 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=max_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- For a less spiky worst-case signal, `quantile_over_time(0.99, ...)` ignores the single most extreme sample.
