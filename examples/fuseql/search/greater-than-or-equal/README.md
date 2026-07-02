# >= (greater than or equal)

Numeric comparison filter operator. Selects log lines where a numeric facet value is greater than or equal to the specified number. The boundary value is included.

## Syntax

```fuseql
@facetName>=number
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `@facetName` | Yes | A numeric facet name, prefixed with `@`. |
| `number` | Yes | The inclusive lower bound; values equal to or greater than this are returned. |

## Example

Return nginx logs for all successful or error responses (status >= 200).

```fuseql
source="nginx" @http_status>=200 | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse | 13,277 |
| kfuse-ingress | 2,310,176 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @http_status>=200 | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Use `>=` when the boundary value should be included in the result set.
- Pair with `<=` to form inclusive ranges: `@http_status>=200 and @http_status<=299` selects only 2xx responses.
