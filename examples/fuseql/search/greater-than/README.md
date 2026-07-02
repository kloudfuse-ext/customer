# > (greater than)

Numeric comparison filter operator. Selects log lines where a numeric facet value is strictly greater than the specified number. Applies only to numeric facets prefixed with `@`.

## Syntax

```fuseql
@facetName>number
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `@facetName` | Yes | A numeric facet name, prefixed with `@`. |
| `number` | Yes | The numeric threshold; only values strictly greater than this are returned. |

## Example

Return nginx logs where the HTTP status code indicates a server error (status > 499).

```fuseql
source="nginx" @http_status>499 | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse-ingress | ~1,500 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @http_status>499 | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Numeric comparison operators (`>`, `>=`, `<`, `<=`) apply only to numeric facets prefixed with `@`.
- The boundary value is excluded — use `>=` to include it.
- Combine multiple numeric comparisons with `and` to create range filters.
