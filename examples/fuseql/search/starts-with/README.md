# *~ (starts with)

Prefix match filter operator. Selects log lines where a label or facet value begins with the specified string. Faster alternative to a regex anchor (`=~"^prefix"`) for simple literal prefix checks.

## Syntax

```fuseql
label*~"prefix"
@facet*~"prefix"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `label` or `@facet` | Yes | The label or facet name to match against. |
| `"prefix"` | Yes | The string that the field value must start with. |

## Example

Return logs from containers whose name starts with `kfuse`.

```fuseql
source="nginx" kube_container_name*~"kfuse" | count by kube_container_name
```

**Expected output (illustrative):**

| kube_container_name | _count |
|---|---|
| kfuse-api-server | ~50,000 |
| kfuse-ingress-nginx | ~2,300,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" kube_container_name*~\\\"kfuse\\\" | count by kube_container_name\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The `*~` operator is case-sensitive.
- For case-insensitive prefix matching, use the regex operator: `label=~"(?i)^prefix"`.
- Prefer `*~` over a regex prefix pattern when the match is purely literal — it is more readable.
