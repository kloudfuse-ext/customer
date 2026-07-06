# count_over_time

Counts the log lines of each stream within the range window. This is the fundamental log-to-metric operator: wrap it in `sum by (...)` to chart log volume by any label, or compare error counts across services and levels.

## Syntax

```
count_over_time({<selector>} [<pipeline>] [<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<selector>` | Required | Stream selector, optionally followed by a filter/parser pipeline. |
| `<range>` | Required | The window to count over, such as `[1m]`, `[5m]`, or `[1h]`. |

## Example

Count Grafana log lines by level over the last five minutes. The `sum by (level)` aggregation collapses the per-stream counts into one series per level.

<!-- validation: kind=instant minutes=10 -->
```logql
sum by (level) (count_over_time({source="grafana"}[5m]))
```

**Expected output:**

| level | Value |
|---|---|
| debug | 7,900 |
| error | 63,685 |
| info | 75,079 |
| warn | 11 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (level) (count_over_time({source="grafana"}[5m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- In a range query (as charted on a dashboard), the window slides: each evaluation step counts the lines in the trailing `<range>` interval.
