# subquery

Executes a nested inner query, converts its results into a filter expression using `compose`, and applies that filter to the outer query. Use `subquery` to correlate data across sources — for example, finding logs from hosts that also appear in a separate error log source.

## Syntax

```fuseql
[subquery: <inner_query> | compose <fields> [maxresults=<N>] [keywords]]
```

The subquery block can appear in three positions:

```fuseql
[subquery: <inner_query> | compose <fields>] | <outer_query>

<outer_query> | where [subquery: <inner_query> | compose <fields>]

<outer_query> | if([subquery: <inner_query> | compose <fields>], <true_value>, <false_value>) as <field>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<inner_query>` | Required | Any valid FuseQL query. Its results are passed to `compose`. |
| `compose <fields>` | Required | Converts inner query results into a boolean filter expression. |
| `maxresults=<N>` | Optional | Limits rows used by `compose`. Default: 2500. Maximum: 10000. |
| `keywords` | Optional | Generates keyword grep searches. Not supported with `where` or `if`. |

## Example

Filter logs from `pisco-shared` to only those originating from hosts that appear in query-service logs.

```fuseql
org_id="pisco-shared"
and [subquery: source="query-service" | count by host | compose host]
| timeslice 20s
| count by _timeslice
```

The inner query produces hosts `server-1` and `server-2`, generating the filter:
`((host="server-1") or (host="server-2"))`

**Expected output (illustrative):**

| _timeslice | _count |
|---|---|
| 2026-06-27 18:53:00 UTC | 124,832 |
| 2026-06-27 18:53:20 UTC | 98,441 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"org_id=\\\"pisco-shared\\\" and [subquery: source=\\\"query-service\\\" | count by host | compose host] | timeslice 20s | count by _timeslice\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Always test the outer query independently before adding the inner subquery.
- Subqueries within `if` or `where` are typically more expensive than at the start of the search expression.
- Subqueries are not supported in Scheduled Views.
- The `subquery` operator must always include `compose` as its final stage.
