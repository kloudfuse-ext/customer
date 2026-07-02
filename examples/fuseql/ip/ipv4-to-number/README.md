# ipv4tonumber

Converts an IPv4 address from dot-decimal notation to its equivalent 32-bit unsigned decimal integer. Useful for numeric range comparisons, sorting IPs arithmetically, and subnet boundary calculations.

## Syntax

```fuseql
| ipv4tonumber(<ipv4String>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<ipv4String>` | Yes | A string field or literal containing a dot-decimal IPv4 address. |
| `as <alias>` | Yes | Name for the numeric output column. |

## Example

Convert client IPs from nginx access logs to their decimal representation.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| ipv4tonumber(ip) as ip_num
| first(ip_num) as example_ip_num
```

**Expected output (illustrative):**

| example_ip_num |
|---|
| 168559106 |

Values shown are illustrative; actual output depends on your data. `ipv4tonumber("10.2.132.2")` = 168559106.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | ipv4tonumber(ip) as ip_num | first(ip_num) as example_ip_num\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The formula is: `(octet1 × 16777216) + (octet2 × 65536) + (octet3 × 256) + octet4`.
- Use the numeric result with `>` and `<` filters to perform efficient subnet range checks without string manipulation.
- Only IPv4 (dot-decimal) addresses are supported; validate with `isvalidip` first if the input may be mixed.
