# Not equal (!=)

Selects time series whose label value is not equal to the given string. Use it to exclude one known series from an otherwise broad selection.

## Syntax

```
<metric>{<label>!="<value>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The label to test. |
| `<value>` | Required | The string value to exclude. |

## Example

Count goroutines across Kloudfuse services excluding the query-service, grouped by service name.

<!-- validation: kind=instant minutes=10 -->
```promql
sum by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_instance="kfuse", app_kubernetes_io_name!="query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| rum-query-service | 1,302 |
| zapper | 2,567 |
| config-mgmt-service | 725 |
| ingester | 98,322 |
| envoy-gateway | 1,927 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_instance="kfuse", app_kubernetes_io_name!="query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Pair negative matchers with at least one positive matcher — a selector of only negations reads every series of the metric.
