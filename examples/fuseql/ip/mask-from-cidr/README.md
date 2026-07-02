# maskfromcidr

Returns the IPv4 subnet mask string that corresponds to a given CIDR prefix length. The result is a dot-decimal string such as `255.255.255.0`.

## Syntax

```fuseql
| maskfromcidr(<prefixLength>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<prefixLength>` | Yes | An integer from 0 to 32 specifying the CIDR prefix length. |
| `as <alias>` | Yes | Name for the string output column. |

## Example

Compute the subnet mask for a /24 network.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| maskfromcidr(24) as subnet_mask
| first(subnet_mask) as mask
```

**Expected output (illustrative):**

| mask |
|---|
| 255.255.255.0 |

Values shown are illustrative; actual output depends on your data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | maskfromcidr(24) as subnet_mask | first(subnet_mask) as mask\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Common results: `/8` → `255.0.0.0`, `/16` → `255.255.0.0`, `/24` → `255.255.255.0`, `/32` → `255.255.255.255`.
- The prefix length must be between 0 and 32 inclusive.
- Use together with `getcidrprefix` and `comparecidrprefix` for complete subnet analysis workflows.
