# !term (not terms exist)

Token exclusion filter operator. Excludes log lines whose message body contains the specified whole token or all of the specified tokens. Tokens are whitespace- and punctuation-delimited words determined at log ingestion.

## Syntax

```fuseql
!term
!term1 term2 term3
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `!term` | Yes | One or more unquoted tokens to exclude. A log line is excluded if it contains all listed tokens. |

## Example

Return nginx logs that do not contain the token `health`.

```fuseql
source="nginx" !health | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse | 13,277 |
| kfuse-ingress | ~2,309,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" !health | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `!term` matches whole tokens only — it will not exclude a token that merely contains the string as a substring (e.g. `!health` will not exclude `healthcheck`).
- To exclude substring matches, use the not-grep operator (`!"health"`).
- When multiple tokens are listed (`!term1 term2`), a line is excluded only if it contains all listed tokens.
