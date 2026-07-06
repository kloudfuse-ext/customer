# Regex not match (!~)

Selects time series whose label value does not match an RE2 regular expression. One `!~` matcher can exclude several values at once via alternation.

## Syntax

```
<metric>{<label>!~"<regex>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The label to test. |
| `<regex>` | Required | An anchored RE2 expression; fully matching series are excluded. |

## Example

Count goroutines for Kloudfuse services that are not one of the query services.

<!-- validation: kind=instant minutes=10 -->
```promql
sum by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_instance="kfuse", app_kubernetes_io_name!~".*query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| envoy-gateway | 1,926 |
| zapper | 2,570 |
| kfuse-grafana | 60,471 |
| trace-transformer | 97,843 |
| hydration-service | 558 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_instance="kfuse", app_kubernetes_io_name!~".*query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Like `=~`, the expression is anchored against the whole label value.
