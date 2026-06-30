# isprivateip

Checks whether an IPv4 address falls within a private (RFC 1918) address range. Returns `true` for 10.0.0.0/8, 172.16.0.0/12, and 192.168.0.0/16 ranges; `false` for all other addresses.

## Syntax

```fuseql
| isprivateip(<ipv4String>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<ipv4String>` | Yes | A string field or literal containing an IPv4 address. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Parse nginx access logs, extract the client IP, and count log lines by whether the IP is private or public.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| isprivateip(ip) as is_private
| count by is_private
```

**Expected output:**

| is_private | _count |
|---|---|
| True | 2,056,834 |
| False | 11,332 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | isprivateip(ip) as is_private | count by is_private\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `isprivateip` is the logical complement of `ispublicip`.
- In Kubernetes environments, most pod-to-pod traffic originates from 10.x.x.x addresses, so `True` counts are typically very high.
- Filter on `is_private=False` to focus on external client traffic for security analysis.
