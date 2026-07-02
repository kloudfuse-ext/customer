# =~ (regex)

Regex match filter operator. Selects log lines where a label or facet value matches the specified RE2-compliant regular expression pattern. The match is applied as a substring search unless anchored with `^` and `$`.

## Syntax

```fuseql
label=~"pattern"
@facetName=~"pattern"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `label` or `@facetName` | Yes | The label or facet name to match against. |
| `"pattern"` | Yes | A RE2-compliant regular expression string. |

## Example

Return nginx logs from any namespace whose name starts with `kfuse`.

```fuseql
source="nginx" kube_namespace=~"kfuse.*" | count by kube_namespace
```

**Expected output:**

| kube_namespace | _count |
|---|---|
| kfuse | 13,277 |
| kfuse-ingress | 2,310,176 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" kube_namespace=~\\\"kfuse.*\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- FuseQL uses RE2 syntax — look-ahead and look-behind assertions are not supported.
- For full-value matching, anchor the pattern: `label=~"^exact-value$"`.
- For case-insensitive matching, use the RE2 flag: `label=~"(?i)nginx"`.
