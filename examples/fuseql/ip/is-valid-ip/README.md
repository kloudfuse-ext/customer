# isvalidip

Checks whether an IPv4 or IPv6 address string is syntactically valid. Returns `true` if the address conforms to the correct format and falls within the allowed range, `false` otherwise.

## Syntax

```fuseql
| isvalidip(<ipString>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<ipString>` | Yes | A string field or literal containing an IPv4 or IPv6 address. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Parse nginx access logs, extract the client IP, and classify each log line as having a valid IP address.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| isvalidip(ip) as valid_ip
| count by valid_ip
```

**Expected output:**

| valid_ip | _count |
|---|---|
| True | 65,272,810 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | isvalidip(ip) as valid_ip | count by valid_ip\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- All IP addresses extracted from well-formed nginx access log lines are valid, so `isvalidip` is most useful for catching malformed or missing IP fields.
- Use `isvalidip` as a guard before passing IP fields to operators like `ispublicip` or `getcidrprefix`, which require valid input.
- Both IPv4 (e.g. `192.168.0.1`) and IPv6 (e.g. `::1`) addresses are supported.
