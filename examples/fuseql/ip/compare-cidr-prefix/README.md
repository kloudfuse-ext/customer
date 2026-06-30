# comparecidrprefix

Checks whether two IPv4 addresses share the same network prefix at a given CIDR prefix length. Returns `true` if both addresses fall within the same subnet, `false` otherwise.

## Syntax

```fuseql
| comparecidrprefix(<ipv4String1>, <ipv4String2>, <prefixLength>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<ipv4String1>` | Yes | A string field or literal containing the first IPv4 address. |
| `<ipv4String2>` | Yes | A string field or literal containing the second IPv4 address (typically the network base address). |
| `<prefixLength>` | Yes | An integer from 0 to 32 specifying the number of network bits to compare. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Check whether client IPs in nginx logs belong to the 10.2.0.0/16 internal subnet.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| comparecidrprefix(ip, "10.2.0.0", 16) as in_subnet
| count by in_subnet
```

**Expected output (illustrative):**

| in_subnet | _count |
|---|---|
| true | 2,056,834 |
| false | 11,332 |

Values shown are illustrative; actual output depends on your data. `comparecidrprefix("10.2.132.2", "10.2.0.0", 16)` = `true`.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | comparecidrprefix(ip, \\\"10.2.0.0\\\", 16) as in_subnet | count by in_subnet\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- More efficient than string prefix matching for subnet membership tests.
- The second argument is typically a network base address (host bits zeroed), but any IP within the subnet works — both addresses are masked before comparison.
- Use `| where in_subnet` to filter down to only traffic from the target subnet.
