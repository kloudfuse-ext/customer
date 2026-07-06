# sum_over_time

Adds up all unwrapped values within the range window. Use it for quantities that accumulate — total bytes transferred, total items processed, or total time spent — rather than for point-in-time measurements.

## Syntax

```
sum_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to sum over. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Total the time Grafana spent waiting on each datasource endpoint in the last five minutes — request count times average latency, in one number per endpoint.

<!-- validation: kind=instant minutes=10 -->
```logql
sum_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 560.41 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- With `duration()` conversion the sum is in seconds.
