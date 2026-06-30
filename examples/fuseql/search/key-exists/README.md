# key exists

Facet presence filter operator. Selects log lines where a specific facet key is present, regardless of the value it holds. In regular search, use the `key exists` keyword syntax; in advanced search, reference the facet name with the `@` prefix alone.

## Syntax

**Regular search:**
```fuseql
key exists="facetName"
```

**Advanced search:**
```fuseql
@facetName
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `facetName` | Yes | The name of the facet whose presence to check. In regular search, quoted as a string value; in advanced search, prefixed with `@`. |

## Example

Return log lines that have a `user_agent_original` facet (any value).

```fuseql
source="nginx" @user_agent_original | count by kube_namespace
```

**Expected output (illustrative):**

| kube_namespace | _count |
|---|---|
| kfuse-ingress | ~2,300,000 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" @user_agent_original | count by kube_namespace\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Use `key exists` to identify log lines enriched with a specific facet, or to find entries from agents or integrations that emit a particular field.
- Combine with value operators to narrow results: `@user_agent_original and @user_agent_original!~".*bot.*"`.
- The advanced search form (`@facetName` alone) is the most concise way to express facet presence.
