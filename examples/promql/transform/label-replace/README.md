# label_replace

Adds or overwrites a label on every series by matching a regular expression against an existing label and expanding a replacement template with the capture groups. Series whose source label does not match pass through unchanged.

## Syntax

```
label_replace(<expr>, "<dst>", "<replacement>", "<src>", "<regex>")
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expr>` | Required | The expression to transform. |
| `<dst>` | Required | The label to write. |
| `<replacement>` | Required | Template for the new value; `$1`, `$2` reference capture groups. |
| `<src>` | Required | The label to match against. |
| `<regex>` | Required | An anchored RE2 expression. |

## Example

Derive a short `service` label from `app_kubernetes_io_name` by stripping the `-service` suffix.

<!-- validation: kind=instant minutes=10 -->
```promql
label_replace(
  sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"}),
  "service", "$1", "app_kubernetes_io_name", "(.*)-service"
)
```

**Expected output:**

| service | Value |
|---|---|
| rum-query | 1,316 |
| query | 64,523 |
| trace-query | 3,058 |
| logs-query | 19,486 |
| events-query | 3,019 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=label_replace( sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_name=~".*query-service"}), "service", "$1", "app_kubernetes_io_name", "(.*)-service" )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- The source label is left untouched; drop it from view with a surrounding aggregation if needed.
