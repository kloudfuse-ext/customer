# Regex match (=~)

Selects time series whose label value matches an RE2 regular expression. The expression is fully anchored — it must match the entire label value. Use it to select a family of related series in one matcher.

## Syntax

```
<metric>{<label>=~"<regex>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The label to test. |
| `<regex>` | Required | An RE2 regular expression, anchored at both ends of the value. |

## Example

Select goroutine gauges for every Kloudfuse query service — `query-service`, `events-query-service`, and `rum-query-service` all match the expression.

<!-- validation: kind=instant minutes=10 -->
```promql
sum by (app_kubernetes_io_name) (
  go_goroutines{app_kubernetes_io_name=~".*query-service"}
)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| rum-query-service | 1,312 |
| logs-query-service | 19,541 |
| query-service | 64,555 |
| trace-query-service | 3,052 |
| events-query-service | 3,017 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=sum by (app_kubernetes_io_name) ( go_goroutines{app_kubernetes_io_name=~".*query-service"} )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Because the match is anchored, `=~"query"` matches only the exact value `query`; use `.*query.*` for a contains match.
- Prefer `=` when you know the exact value — equality matchers resolve faster than regex.
