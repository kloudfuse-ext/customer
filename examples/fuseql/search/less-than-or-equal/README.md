# <= (less than or equal)

Numeric comparison filter operator. Selects log lines where a numeric facet value is less than or equal to the specified number. The boundary value is included.

## Syntax

```fuseql
@facetName<=number
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `@facetName` | Yes | A numeric facet name, prefixed with `@`. |
| `number` | Yes | The inclusive upper bound; values equal to or less than this are returned. |

## Example

Return nginx logs for requests that did not return a server error (status code 499 or below).

```fuseql
source="nginx" @http_status<=499 | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse | 13,277 |
| kfuse-ingress | ~2,308,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @http_status<=499 | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Use `<=` when the boundary value should be included.
- Combine with `>=` to form inclusive ranges: `@http_status>=400 and @http_status<=499` selects all 4xx responses.
