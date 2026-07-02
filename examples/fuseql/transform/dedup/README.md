# dedup

Removes duplicate log lines, retaining only one row per unique combination of the specified fields. Optionally keep the first N duplicate rows per group. Use `dedup` to collapse repeated log events — for example, keeping only the first occurrence of each unique error per source.

## Syntax

```fuseql
| dedup by <field1>[, <field2>, ...]
| dedup <n> by <field1>[, <field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `by <field1>, ...` | Required | Fields that define uniqueness. Rows with the same values for all listed fields are duplicates. |
| `<n>` | Optional | Number of rows to keep per unique group. Defaults to `1`. |

## Example

Parse nginx logs and keep only the first log line per unique HTTP method + status code combination.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| dedup by method, status
```

**Expected output (illustrative — one row per unique method+status pair):**

| method | status | url |
|---|---|---|
| GET | 200 | /index.html |
| POST | 201 | /api/users |
| GET | 404 | /missing.html |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | dedup by method, status\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `dedup` operates in the Advanced Search log streaming view.
- In the tabular aggregation pipeline, prefer `count_unique` or `by` grouping for deduplication semantics.
- Set `<n>` to keep the first N occurrences per group rather than just one.
