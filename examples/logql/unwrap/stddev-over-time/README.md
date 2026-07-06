# stddev_over_time

Computes the population standard deviation of the unwrapped values within the range window. A rising standard deviation with a flat average means the value is becoming erratic — an early sign of saturation or contention.

## Syntax

```
stddev_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to compute over. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Measure how much Grafana datasource latency varies per endpoint over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
stddev_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 1.113 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=stddev_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `stdvar_over_time` returns the variance — the square of this value.
