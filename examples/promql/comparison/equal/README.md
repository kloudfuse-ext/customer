# Equal (=)

Selects time series whose label value is exactly equal to the given string. Matchers appear in curly braces after the metric name; every additional matcher narrows the series set the query reads, which is the single biggest lever on query cost.

## Syntax

```
<metric>{<label>="<value>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | A label on the metric, such as `kube_namespace`, `app_kubernetes_io_name`, or `availability_zone`. |
| `<value>` | Required | The exact string to match; case-sensitive. |

## Example

Select the goroutine-count gauge for the Kloudfuse query-service only, then sum it into a single series.

<!-- validation: kind=instant minutes=10 -->
```promql
sum(go_goroutines{app_kubernetes_io_name="query-service"})
```

**Expected output:**

| Value |
|---|
| 64,531 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum(go_goroutines{app_kubernetes_io_name="query-service"})' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Combine matchers with commas: `{app_kubernetes_io_instance="kfuse", availability_zone="us-east-1b"}`. All must hold at once.
- A bare metric name with no matchers selects every series of that metric across all sources.
