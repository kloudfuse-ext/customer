# stddev

Computes the standard deviation of a numeric field across matched log lines. `stddev` measures how spread out values are around the mean — a low value indicates that most log lines have similar values, while a high value indicates erratic or inconsistent behaviour. Null or missing field values are ignored.

## Syntax

```fuseql
| stddev(<field>) [as <alias>] [by <field1>, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The numeric field to compute the standard deviation of. Null or missing values are ignored. |
| `as <alias>` | Optional | Renames the output column. Defaults to `_stddev`. |
| `by <field1>, ...` | Optional | Groups results by one or more fields. Without `by`, returns a single aggregate row. |

## Example

Parse nginx access logs and measure the consistency of response body sizes per HTTP method. A very high standard deviation for GET (1,073,687 bytes) reflects that GET responses range from zero-byte 304 responses to multi-megabyte payloads.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| stddev(bytes) as stddev_bytes by method
```

**Expected output:**

| method | stddev_bytes |
|---|---|
| GET | 1,073,687.61 |
| POST | 1,894.84 |
| OPTIONS | 69.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | stddev(bytes) as stddev_bytes by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `stddev` is in the same unit as the input (bytes). A high `stddev` relative to `avg` signals a wide mix of response sizes — normal for GET endpoints that serve both small API responses and large file downloads.
- `stddev` is expressed in the same unit as the input field, making it easy to interpret alongside `avg`.
- Prefer `stddev` over `stdvar` when you need a human-readable measure of spread in the original unit.
