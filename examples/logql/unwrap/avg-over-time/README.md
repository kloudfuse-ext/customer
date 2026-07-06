# avg_over_time

Computes the arithmetic mean of the unwrapped values within the range window. This is the go-to statistic for typical latency or size per group — pair it with `max_over_time` or `quantile_over_time` to see the tail as well.

## Syntax

```
avg_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to average over. |
| `by (<labels>)` | Optional | Grouping labels; without it, every label combination produces its own series. |

## Example

Average the duration of Grafana datasource requests per endpoint over the last five minutes. The `duration()` conversion parses values like `28.8ms` into seconds.

<!-- validation: kind=instant minutes=10 -->
```logql
avg_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 0.1312 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=avg_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Averages hide outliers; check `quantile_over_time(0.95, ...)` or `max_over_time` when hunting slow requests.
