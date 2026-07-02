# hash

Hashes a field value into a fixed-length string using a specified algorithm. Use `hash` to anonymize sensitive fields — such as IP addresses or user identifiers — while still allowing grouping and cardinality counting without exposing original values.

## Syntax

```
| hash(<field>) as <alias>

| hash(<field>, <hashAlgorithm>) as <alias>
```

Supported algorithms: `md5` (default), `sha1`, `sha2_256`, `murmur3_128`.

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The string field or literal to hash. |
| `<hashAlgorithm>` | Optional | The hash algorithm. Defaults to `md5`. Options: `md5`, `sha1`, `sha2_256`, `murmur3_128`. |
| `<alias>` | Required | Name for the resulting hash field. |

## Example

Hash client IP addresses and count unique hashed IPs to measure distinct client cardinality without exposing real addresses.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| hash(ip) as ip_hash
| count_unique(ip_hash) as unique_ips
```

**Expected output:**

| unique_ips |
|---|
| 1,167 |

> Result is confirmed from a 5-minute nginx log window.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | hash(ip) as ip_hash | count_unique(ip_hash) as unique_ips\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Default algorithm is MD5; use `sha1` or `sha2_256` for stronger cryptographic guarantees.
- Use `murmur3_128` for higher performance when cryptographic strength is not required.
- Hashing is one-way — original values cannot be recovered from the hash.
