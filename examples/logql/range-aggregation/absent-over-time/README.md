# absent_over_time

Returns a single series with value `1` when the selector matches no log lines in the range window, and returns nothing when lines exist. This inversion is what alerting needs for silence detection: a service that has stopped logging entirely produces no series for a normal alert rule to fire on.

## Syntax

```
absent_over_time({<selector>} [<pipeline>] [<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<selector>` | Required | Stream selector, optionally followed by a filter/parser pipeline. |
| `<range>` | Required | The silence window, such as `[5m]` or `[15m]`. |

## Example

Check whether a service has logged anything in the last five minutes. Because no `payments-service` source exists on this cluster, the query returns `1` — the signal an alert rule would fire on.

<!-- validation: kind=instant minutes=10 -->
```logql
absent_over_time({source="payments-service"}[5m])
```

**Expected output:**

| source | Value |
|---|---|
| payments-service | 1 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=absent_over_time({source="payments-service"}[5m])' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- When log lines exist, the result is empty — dashboards show no data, and alert rules do not fire.
- The returned series carries the equality matchers from the selector as labels, so the alert knows which service went silent.
