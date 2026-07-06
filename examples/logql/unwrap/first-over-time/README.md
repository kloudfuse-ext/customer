# first_over_time

Returns the first (oldest) unwrapped value within the range window. Use it together with `last_over_time` to measure how a value changed across the window — for example, a gauge reported in logs.

## Syntax

```
first_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to select from. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Read the duration of the oldest Grafana datasource request in the window, per endpoint.

<!-- validation: kind=instant minutes=10 -->
```logql
first_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 8.5353e-05 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=first_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `first_over_time` and `last_over_time` order samples by timestamp, not by value.
