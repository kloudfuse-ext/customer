# stdvar_over_time

Computes the population variance of the unwrapped values within the range window — the square of the standard deviation. Variance is additive across independent components, which occasionally makes it the more convenient form in capacity math.

## Syntax

```
stdvar_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to compute over. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Compute the variance of Grafana datasource latency per endpoint over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
stdvar_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 1.195 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=stdvar_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- For a value in the same unit as the samples, use `stddev_over_time`.
