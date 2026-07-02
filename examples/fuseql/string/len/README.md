# len

Returns the number of characters in a string. Use `len` to measure field lengths for filtering, aggregation, or anomaly detection — for example, finding unusually long URLs that may indicate malformed requests.

## Syntax

```
| len(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | A string field or literal whose length to measure. |
| `<alias>` | Required | Name for the resulting numeric field. |

## Example

Calculate the average URL length by HTTP method to identify which method types produce longer request paths.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| len(url) as url_len
| avg(url_len) as avg_url_len by method
```

**Expected output:**

| method | avg_url_len |
|---|---|
| GET | 31.4 |
| POST | 26.8 |
| HEAD | 27.1 |

> Values shown are illustrative; actual results depend on your log data.

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | len(url) as url_len | avg(url_len) as avg_url_len by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Combine `len` with `where` to filter out-of-range values, for example `| where len(url) > 200`.
- Returns an integer count of characters (not bytes).
