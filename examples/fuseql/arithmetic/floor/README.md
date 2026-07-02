# floor

Rounds a number down to the nearest integer (floor function). Use `floor` to truncate fractional values or bucket a continuous metric into discrete integer bins.

## Syntax

```fuseql
| floor(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Express nginx traffic in thousands of requests per minute (rounded down).

```fuseql
source="nginx"
| timeslice 1m
| count as requests by _timeslice
| floor(requests / 1000) as krequests
```

**Expected output:**

| _timeslice | requests | krequests |
|---|---|---|
| 2026-06-27 18:53:00 UTC | 61,441 | 61 |
| 2026-06-27 18:54:00 UTC | 650,712 | 650 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1m | count as requests by _timeslice | floor(requests / 1000) as krequests\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `floor(3.99)` returns `3`. `floor(-3.2)` returns `-4` (toward negative infinity).
- To always round up, use `ceil`. To round to the nearest integer, use `round`.
