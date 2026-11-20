# or

Union operator (OR logic) between two search filter conditions. Selects log lines that satisfy at least one of the conditions. Write the keyword `or` between two full conditions; `OR` also works.

## Syntax

**Labels:**
```fuseql
label="valueA" or label="valueB"
```

**Facets:**
```fuseql
@facet="valueA" or @facet="valueB"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| left condition | Yes | A search filter expression on a label, facet, or term. |
| right condition | Yes | A second search filter expression; at least one must match. |

## Example

Count grafana logs whose level is either `info` or `warn`.

```fuseql
source="grafana" and (level="info" or level="warn") | count by level
```

**Expected output:**

| level | _count |
|---|---|
| warn | 206 |
| info | 540,664 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"grafana\\\" and (level=\\\"info\\\" or level=\\\"warn\\\") | count by level\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- Write each alternative as a full condition. A single quoted value such as `level="info OR warn"` is matched literally, so it returns no log lines. Verified against Kloudfuse 4.4.0.
- Use parentheses to group the alternatives. Without them, `source="grafana" and level="info" or level="warn"` is read as `(source="grafana" and level="info") or level="warn"`, so it also returns `warn` lines from every other source.
- `level` (a label) and `@level` (a facet) can match different sets of logs. Use the same one on both sides of `or`.
