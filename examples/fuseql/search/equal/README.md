# = (equal)

Exact-match filter operator. Selects log lines where a label or facet equals the specified value exactly. Case-sensitive. Use `label=` for Kubernetes/infrastructure labels and `@facet=` for indexed log fields in advanced search.

## Syntax

```fuseql
label="value"
@facetName="value"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `label` or `@facetName` | Yes | The label key or (with `@` prefix) facet name to filter on. |
| `"value"` | Yes | The exact string value the field must equal. |

## Example

Select nginx access logs from a specific Kubernetes namespace and count by namespace.

```fuseql
source="nginx" kube_namespace="kfuse" | count by kube_namespace
```

**Expected output:**

| kube_namespace | _count |
|---|---|
| kfuse | 13,277 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" kube_namespace=\\\"kfuse\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The `=` operator performs an exact, case-sensitive match.
- `source` is a special system label available in all FuseQL queries and is not prefixed with `@`.
- For substring matching use `**` (contains); for pattern matching use `=~` (regex).
