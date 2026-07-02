# == (facet terms exist)

Exact facet term match operator. Searches for log lines where a facet has a specific indexed term value. Unlike `=` (value equality), `==` matches against tokenized index terms.

## Syntax

```fuseql
@facetName=="value"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `@facetName` | Yes | The facet name, prefixed with `@`. |
| `"value"` | Yes | The exact indexed term value the facet must contain. |

## Example

Return log lines where the `traceFlags` facet has the indexed term value `1`.

```fuseql
source="nginx" @traceFlags=="1" | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse-ingress | ~500 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @traceFlags==\\\"1\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `==` performs a term-based lookup against the inverted index and is faster than `=` for facets with many distinct values.
- Use `=` for simple string equality on labels; use `==` for exact term lookups on indexed facet fields.
