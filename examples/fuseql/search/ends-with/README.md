# ~* (ends with)

Suffix match filter operator. Selects log lines where a label or facet value ends with the specified string. Faster alternative to a regex anchor (`=~"suffix$"`) for simple literal suffix checks.

## Syntax

```fuseql
label~*"suffix"
@facet~*"suffix"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `label` or `@facet` | Yes | The label or facet name to match against. |
| `"suffix"` | Yes | The string that the field value must end with. |

## Example

Return logs from services whose name ends with `service`.

```fuseql
source="nginx" @resource_service_name~*"service" | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse | ~8,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @resource_service_name~*\\\"service\\\" | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The `~*` operator is case-sensitive.
- For case-insensitive suffix matching, use the regex operator: `label=~"(?i)suffix$"`.
- Prefer `~*` over a regex suffix pattern when the match is a plain literal string.
