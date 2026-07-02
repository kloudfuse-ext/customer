# tobytes

Converts a human-readable storage size string (such as `1.5KB` or `2MB`) into the equivalent number of bytes as an integer. Use `tobytes` to normalize size fields that arrive in mixed units before aggregating or comparing them.

## Syntax

```
| tobytes(<storageSize>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<storageSize>` | Required | A string field or literal representing a size with a unit suffix. Supported units: `B`, `KB`, `MB`, `GB`, `TB`. |
| `<alias>` | Required | Name for the resulting integer field (bytes). |

## Example

Convert a static size string of `2MB` to its byte equivalent.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| tobytes("2MB") as size_bytes
| first(size_bytes) by method
```

**Expected output:**

| method | first(size_bytes) |
|---|---|
| GET | 2097152 |
| POST | 2097152 |

> `2MB` = 2 × 1,048,576 = 2,097,152 bytes (binary units: 1 KB = 1,024 bytes).

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | tobytes(\\\"2MB\\\") as size_bytes | first(size_bytes) by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Uses binary units: 1 KB = 1,024 bytes, 1 MB = 1,048,576 bytes.
- The unit suffix must be part of the string argument (e.g., `"2MB"` not `"2"`).
