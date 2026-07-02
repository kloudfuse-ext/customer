# !~ (not regex)

Regex exclusion filter operator. Selects log lines where a label or facet value does not match the specified RE2-compliant regular expression pattern. The logical complement of `=~`.

## Syntax

```fuseql
label!~"pattern"
@facetName!~"pattern"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `label` or `@facetName` | Yes | The label or facet name to match against. |
| `"pattern"` | Yes | A RE2-compliant regular expression string; lines where the value matches are excluded. |

## Example

Return nginx logs from namespaces that do not contain `kfuse`.

```fuseql
source="nginx" kube_namespace!~"kfuse.*" | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| other-ns | ~5,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" kube_namespace!~\\\"kfuse.*\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `!~` excludes lines where the pattern matches anywhere in the field value.
- To exclude only full-value matches, anchor the pattern: `label!~"^exact-value$"`.
- FuseQL uses RE2 syntax — look-ahead and look-behind assertions are not supported.
