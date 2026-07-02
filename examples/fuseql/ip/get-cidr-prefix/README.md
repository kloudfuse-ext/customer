# getcidrprefix

Returns the network address (prefix) for an IPv4 address given a CIDR prefix length. The host bits are zeroed out to produce the network identifier. Use this to group IP addresses by subnet.

## Syntax

```fuseql
| getcidrprefix(<ipv4String>, <prefixLength>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<ipv4String>` | Yes | A string field or literal containing a dot-decimal IPv4 address. |
| `<prefixLength>` | Yes | An integer from 0 to 32 specifying the number of network bits. |
| `as <alias>` | Yes | Name for the string output column. |

## Example

Extract the /16 network prefix from client IPs in nginx logs to group traffic by subnet.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| getcidrprefix(ip, 16) as subnet
| count by subnet
| sort by _count desc
| limit 5
```

**Expected output (illustrative):**

| subnet | _count |
|---|---|
| 10.2.0.0 | 2,056,834 |

Values shown are illustrative; actual output depends on your data. `getcidrprefix("10.2.132.2", 16)` = `"10.2.0.0"`.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | getcidrprefix(ip, 16) as subnet | count by subnet | sort by _count desc | limit 5\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Adjust the prefix length to zoom in or out: `/24` for individual host subnets, `/16` for broader network blocks, `/8` for class-A network grouping.
- The result is a string in dot-decimal notation (e.g. `"10.2.0.0"`), not a numeric value.
- Use alongside `comparecidrprefix` to test whether a specific IP belongs to a target subnet.
