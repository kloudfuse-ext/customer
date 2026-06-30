# compose

Converts query results into a FuseQL filter expression (a boolean OR of field=value conditions). Primarily used as the final stage of a `subquery`, but can also be run standalone to preview the generated filter.

## Syntax

```fuseql
| compose <field1>[, <field2>, ...] [maxresults=<N>] [keywords]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field1>, ...` | Required | One or more field names. Multiple fields create AND conditions per row; rows are combined with OR. |
| `maxresults=<N>` | Optional | Limits result rows used in filter generation. Default: 2500. Maximum: 10000. |
| `keywords` | Optional | Generates keyword grep searches instead of field equality filters. |

## Example

Generate a filter from level and org_id combinations in query-service logs.

```fuseql
source="query-service"
| count by level, org_id
| compose level, org_id
```

**Expected output:**

| _filter |
|---|
| ((level="error" and org_id="pisco-shared") or (level="info" and org_id="pisco-shared")) |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"query-service\\\" | count by level, org_id | compose level, org_id\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `compose` is most powerful inside a `subquery` block to dynamically filter an outer query.
- Run `compose` standalone first to verify the filter size before embedding in a production subquery.
- The `keywords` flag is not supported inside `where` or `if` clauses.
