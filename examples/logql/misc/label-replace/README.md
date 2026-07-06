# label_replace

Adds or overwrites a label on every series by matching a regular expression against an existing label and expanding a replacement template with the capture groups. The original label is untouched. Use it to normalize names before joining two query results or to display friendlier series names.

## Syntax

```
label_replace(<expr>, "<dst>", "<replacement>", "<src>", "<regex>")
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expr>` | Required | The metric expression to transform. |
| `<dst>` | Required | The label to write. |
| `<replacement>` | Required | Template for the new value; `$1`, `$2` refer to capture groups. |
| `<src>` | Required | The label to match against. |
| `<regex>` | Required | An anchored RE2 expression; when it does not match, the series passes through unchanged. |

## Example

Derive a `service` label from the `source` label on nginx log volume, prefixing it to match a service catalog's naming.

<!-- validation: kind=instant minutes=10 -->
```logql
label_replace(
  sum by (source) (count_over_time({source="nginx"}[5m])),
  "service", "ingress-$1", "source", "(.*)"
)
```

**Expected output:**

| service | source | Value |
|---|---|---|
| ingress-nginx | nginx | 5,135,802 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=label_replace( sum by (source) (count_over_time({source="nginx"}[5m])), "service", "ingress-$1", "source", "(.*)" )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- `label_replace` operates on metric query results; to rewrite labels inside a log pipeline, use `label_format`.
