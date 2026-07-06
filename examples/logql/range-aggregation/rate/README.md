# rate

Computes the per-second rate of log lines in the range window — `count_over_time` divided by the window length. Rates are comparable across window sizes, which makes `rate` the usual choice for dashboards and alert thresholds.

## Syntax

```
rate({<selector>} [<pipeline>] [<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<selector>` | Required | Stream selector, optionally followed by a filter/parser pipeline. |
| `<range>` | Required | The window to compute the rate over, such as `[1m]` or `[5m]`. |

## Example

Measure Grafana's logging rate per level in lines per second, averaged over the last five minutes.

<!-- validation: kind=instant minutes=10 -->
```logql
sum by (level) (rate({source="grafana"}[5m]))
```

**Expected output:**

| level | Value |
|---|---|
| debug | 26.4 |
| error | 215.65 |
| info | 255.40 |
| warn | 0.03667 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (level) (rate({source="grafana"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Add a line filter to rate specific events: `rate({source="nginx"} |= "POST" [1m])` charts POST requests per second.
