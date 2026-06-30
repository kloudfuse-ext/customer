# ispublicip

Checks whether an IPv4 address is a public (routable) address. Returns `false` for RFC 1918 private ranges (10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16) and other reserved ranges, `true` for all other addresses.

## Syntax

```fuseql
| ispublicip(<ipv4String>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<ipv4String>` | Yes | A string field or literal containing an IPv4 address. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Parse nginx access logs, extract the client IP, and count log lines by whether the IP is public or private.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| ispublicip(ip) as is_public
| count by is_public
```

**Expected output:**

| is_public | _count |
|---|---|
| False | 2,440,199 |
| True | 14,083 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | ispublicip(ip) as is_public | count by is_public\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- The majority of traffic in this Kubernetes environment originates from private pod addresses, so `False` counts are expected to dominate.
- Filter on `is_public=True` to isolate external client requests for security auditing or geo-IP enrichment.
- `ispublicip` supports only IPv4. Validate addresses with `isvalidip` first if the input may contain IPv6 or malformed strings.
