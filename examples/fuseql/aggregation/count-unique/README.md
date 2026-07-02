# count_unique

Counts the number of distinct values of a field across matched log lines. `count_unique` works on string, UUID, and IP address typed facets. Use it to answer questions like "how many distinct URLs were requested per method?" or "how many unique source IPs made requests in this window?"

## Syntax

```fuseql
| count_unique(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The string, UUID, or IP address facet to count distinct values of. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_count_unique`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and count how many unique URLs were requested for each HTTP method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| count_unique(url) by method
```

**Expected output:**

| method | _count_unique |
|---|---|
| GET | 3,353 |
| POST | 197,143 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | count_unique(url) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `count_unique` works on string, UUID, and IP address typed facets. Fields extracted by `parse` are strings.
- Applying it to a purely numeric field will produce an error. If you need to count distinct numeric values, convert the field to a string first.
- A high `count_unique` relative to `count` means most requests hit different URLs — typical for REST APIs with resource IDs embedded in the path.
