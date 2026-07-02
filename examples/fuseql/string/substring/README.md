# substring

Extracts a portion of a string between a start offset and an optional end offset. Offsets are zero-based; omitting the end offset returns everything from the start offset to the end of the string. Use `substring` to isolate prefixes, suffixes, or fixed-position tokens from structured fields.

## Syntax

```
| substring(<sourceString>, <startOffset>) as <alias>

| substring(<sourceString>, <startOffset>, <endOffset>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<sourceString>` | Required | The string field or literal to extract from. |
| `<startOffset>` | Required | Zero-based index of the first character to include. |
| `<endOffset>` | Optional | Zero-based index of the first character to exclude (exclusive upper bound). Omit to extract to end of string. |
| `<alias>` | Required | Name for the resulting field. |

## Example

Extract the first five characters of each URL as a prefix, then count the number of distinct prefixes per HTTP method.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| substring(url, 1, 5) as url_prefix
| count_unique(url_prefix) as unique_prefixes by method
```

**Expected output:**

| method | unique_prefixes |
|---|---|
| GET | 42 |
| POST | 18 |
| HEAD | 5 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | substring(url, 1, 5) as url_prefix | count_unique(url_prefix) as unique_prefixes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Offsets are zero-based: `substring(s, 0, 5)` returns the first five characters.
- The end offset is exclusive — `substring("hello", 0, 5)` returns `hello`, not `hello `.
- Omitting the end offset extracts from start to end of string.
