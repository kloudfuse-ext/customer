# ! (not grep)

Full-text exclusion operator. Excludes log lines whose message body contains the specified literal, case-sensitive character sequence. The logical complement of the grep (`"expression"`) operator.

## Syntax

```fuseql
!"expression"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `"expression"` | Yes | A quoted literal string; log lines containing this sequence in the message body are excluded. |

## Example

Return nginx logs that do not contain health-check requests.

```fuseql
source="nginx" !"GET /health" | count by kube_namespace
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
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" !\\\"GET /health\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `!` before a quoted string is the not-grep operator — distinct from `!term` (not-terms-exist, which uses unquoted tokens).
- Because not-grep scans raw character sequences, it is slower than token-based exclusions. Combine with label filters to reduce scan volume.
- Use not-grep to suppress noisy health-check or heartbeat lines before aggregating.
