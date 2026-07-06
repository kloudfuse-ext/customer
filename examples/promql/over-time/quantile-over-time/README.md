# quantile_over_time

Computes the given quantile (0 to 1) of each series' samples within the range window.

## Syntax

```
quantile_over_time(<q>, <metric>[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<q>` | Required | The quantile, between 0 and 1. |
| `<range>` | Required | The trailing window to aggregate over. |

## Example

Apply `quantile_over_time` to the query-service goroutine gauge over the last ten minutes, then average across pods for a single row.

<!-- validation: kind=instant minutes=10 -->
```promql
avg by (app_kubernetes_io_name) (quantile_over_time(0.95, go_goroutines{app_kubernetes_io_name="query-service"}[10m]))
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| query-service | 313.15 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=avg by (app_kubernetes_io_name) (quantile_over_time(0.95, go_goroutines{app_kubernetes_io_name="query-service"}[10m]))' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Over-time functions aggregate one series across time; the aggregation operators (`sum`, `avg`, ...) aggregate across series at one instant. Combine both for fleet summaries.
