# transpose

Converts aggregate query results from a long format into a wide tabular format by pivoting row values into column headers. Similar to a pivot table — transforms a long list into a wide table for easy cross-dimension comparison.

## Syntax

```fuseql
| transpose row <row_field1>[, <row_field2>, ...] column <column_field1>[, <column_field2>, ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `row <row_field1>, ...` | Required | Fields whose values become row labels in the output table. |
| `column <column_field1>, ...` | Required | Fields whose unique values become column headers. |

## Example

Pivot nginx request counts by status code — one column per status, one row per time bucket.

```fuseql
source="nginx"
| timeslice 5m
| count by _timeslice, status
| transpose row _timeslice column status
```

**Expected output (illustrative — columns created dynamically):**

| _timeslice | 200 | 404 | 500 |
|---|---|---|---|
| 2026-06-27 18:50:00 UTC | 412,840 | 1,203 | 87 |
| 2026-06-27 18:55:00 UTC | 389,120 | 987 | 62 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 5m | count by _timeslice, status | transpose row _timeslice column status\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `transpose` supports multiple aggregate functions. When using `count` and `avg` together, columns are named `_count|200`, `avg_response|200`, etc.
- The number of output columns equals the number of unique values in the column field(s).
- Particularly useful for formatting dashboard panel data.
