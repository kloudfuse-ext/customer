# key exists

Facet presence filter operator. Selects log lines where a specific facet key is present, regardless of the value it holds. Write the facet name with the `@` prefix and a type suffix, such as `@logger:string`. Prefix it with `!` to select log lines where the facet is absent.

## Syntax

**Key exists:**
```fuseql
@facetName:type
```

**Key absent:**
```fuseql
!@facetName:type
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `facetName` | Yes | The name of the facet whose presence to check, prefixed with `@`. |
| `type` | Yes | The facet's data type, such as `string` or `number`. The suffix is required; `@facetName` alone is a syntax error. |

## Example

Count grafana log lines that have a `logger` facet, with any value.

```fuseql
source="grafana" and @logger:string | count
```

**Expected output:**

| _count |
|---|
| 365,253 |

`source="grafana" and !@logger:string | count` returns the rest (405,841 in the same window); the two counts add up to the source's total (771,094).

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"grafana\\\" and @logger:string | count\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The type suffix is required but does not narrow the match: `@logger:string`, `@logger:number`, and any other suffix select the same log lines. Use `:string` unless you know the facet's type. Verified against Kloudfuse 4.4.0.
- The `key exists="facetName"` form is a syntax error; use `@facetName:type`.
- Combine with value operators to narrow results: `@logger:string and @logger!~".*ngalert.*"`.
