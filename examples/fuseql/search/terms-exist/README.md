# term (terms exist)

Token match filter operator. Selects log lines whose message body contains the specified whole token or all of the specified tokens. Queries the inverted index directly — the fastest full-text search method in FuseQL.

## Syntax

```fuseql
term
term1 term2 term3
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `term` | Yes | One or more unquoted tokens to match. A log line is returned only if it contains all listed tokens (in any order). |

## Example

Return nginx logs that contain the token `error`.

```fuseql
source="nginx" error | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse-ingress | ~450 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" error | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Token matching is the fastest full-text search method — it uses the inverted index directly without scanning raw text.
- Use it when you know the exact whole word. For partial-word or phrase matching, use the grep operator (`"expression"`).
- When multiple tokens are listed (`term1 term2`), all tokens must appear in the log line but can appear in any order.
