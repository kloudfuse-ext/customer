# Reserved fields

FuseQL provides reserved field names that map to the core columns shown in the Log Search results view. Use these fields to filter, extract, or alias primary log attributes without parsing them from the raw log line.

## Field reference

| Field | Maps to | Description |
|---|---|---|
| `__kf_msg` | Message column | The full raw log line text. Regex matching is optimized for improved query performance. |
| `__kf_level` | Level column | The log severity level (e.g., `ERROR`, `WARN`, `INFO`, `DEBUG`). |
| `__kf_source` | Source column | The log source identifier (equivalent to the `source` facet). |

## Example

Filter logs by message pattern, level, and source simultaneously.

```fuseql
__kf_msg =~ "ERROR.*connection.*timeout"
__kf_level = "ERROR"
__kf_source = "nginx"
```

**Expected output (illustrative):**

| _timeslice | __kf_msg | __kf_level | __kf_source |
|---|---|---|---|
| 2026-06-27 18:54:12 UTC | ERROR: connection timeout after 30s | ERROR | nginx |
| 2026-06-27 18:54:58 UTC | ERROR: connection timeout after 30s | ERROR | nginx |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"__kf_msg =~ \\\"ERROR.*connection.*timeout\\\" __kf_level = \\\"ERROR\\\" __kf_source = \\\"nginx\\\"\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Reserved fields are available in all FuseQL contexts: filter expressions, `where` clauses, and pipe stages.
- `__kf_msg` regex matching (`=~`) is particularly efficient — the engine uses index-based substring extraction.
- To reorder default log columns, alias the reserved fields: `* | __kf_msg as LogMessage | __kf_level as LogLevel`.
