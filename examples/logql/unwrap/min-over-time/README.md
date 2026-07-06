# min_over_time

Returns the smallest unwrapped value within the range window. Use it to find the floor of a measurement — the fastest response, the smallest payload — or to verify that a value never drops below an expected baseline.

## Syntax

```
min_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The unwrapped label providing the sample values. |
| `<range>` | Required | The window to take the minimum over. |
| `by (<labels>)` | Optional | Grouping labels. |

## Example

Find the fastest Grafana datasource request per endpoint in the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
min_over_time(
  {source="grafana"} |= "duration="
  | logfmt
  | unwrap duration(duration) [5m]
) by (endpoint)
```

**Expected output:**

| endpoint | Value |
|---|---|
| queryData | 1.3956e-05 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=min_over_time( {source="grafana"} |= "duration=" | logfmt | unwrap duration(duration) [5m] ) by (endpoint)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Combine with `max_over_time` to see the full spread of a value in one dashboard panel.
