# quantile_over_time

Computes the given quantile (0 to 1) of the unwrapped values within the range window. Percentiles are the standard language of latency objectives — p95 and p99 response times straight from access or application logs, no instrumentation required.

## Syntax

```
quantile_over_time(<q>, {<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<q>` | Required | The quantile as a number between 0 and 1, such as `0.95`. |
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to compute over. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Compute the 95th-percentile duration of Grafana datasource requests per endpoint over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
quantile_over_time(0.95,
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 0.16 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=quantile_over_time(0.95, {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Quantiles are computed per group over the raw samples in the window, so they are exact — not an approximation over pre-aggregated buckets.
