# last_over_time

Returns the last (newest) unwrapped value within the range window. This is the right function for gauge-style fields logged periodically — queue length, cache size, connection count — where only the latest reading matters.

## Syntax

```
last_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to select from. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Read the duration of the most recent Grafana datasource request in the window, per endpoint.

<!-- validation: kind=instant minutes=10 -->
```logql
last_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 7.5672e-05 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=last_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Make the range window comfortably larger than the logging interval, or sparse streams return no sample at some steps.
