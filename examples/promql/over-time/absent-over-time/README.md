# absent_over_time

Returns a single series with value 1 when the selector matched no samples anywhere in the range window, and nothing otherwise. The windowed form of `absent`, and the standard silence detector for alerting.

## Syntax

```
absent_over_time(<metric>{<matchers>}[<range>])
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<range>` | Required | The silence window, such as `[10m]`. |

## Example

Check for samples of a metric that does not exist on this cluster — the result is 1, the signal an alert would fire on.

<!-- validation: kind=instant minutes=10 -->
```promql
absent_over_time(nonexistent_demo_metric{app_kubernetes_io_instance="kfuse"}[10m])
```

**Expected output:**

| app_kubernetes_io_instance | Value |
|---|---|
| kfuse | 1 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=absent_over_time(nonexistent_demo_metric{app_kubernetes_io_instance="kfuse"}[10m])' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- When samples exist the result is empty — dashboards show no data and alert rules stay quiet.
