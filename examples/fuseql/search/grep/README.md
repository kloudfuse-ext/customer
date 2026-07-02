# grep ("expression")

Full-text substring search operator. Searches for a literal, case-sensitive character sequence in the log message body. Unlike token-based term matching, `grep` matches character sequences directly — it can find partial words and multi-word phrases.

## Syntax

```fuseql
"expression"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `"expression"` | Yes | A quoted literal string to search for in the log message body. Case-sensitive. |

## Example

Return nginx logs whose message body contains the phrase `GET /health`.

```fuseql
source="nginx" "GET /health" | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse-ingress | ~180 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" \\\"GET /health\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `grep` is case-sensitive and matches character sequences, not whole tokens.
- Use it for phrase searches or partial-word searches where tokenization would miss the match.
- For whole-word (token) searches, use the bare unquoted term syntax — it is faster because it uses the inverted index.
- Combine with label filters (`source=`) to reduce the scan volume before the substring search.
