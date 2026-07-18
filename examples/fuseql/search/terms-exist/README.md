# term (terms exist)

Token match filter operator. Selects log lines whose message body contains the specified whole token or all of the specified tokens. Queries the Lucene inverted index directly — the fastest full-text search method in FuseQL.

> **Important — multi-word is AND, not a phrase search.**
> `'word1 word2'` returns log lines where *both* tokens appear somewhere in the line. The words do not need to be adjacent or in any particular order. For an exact phrase (words adjacent, in order), use grep: `"word1 word2"`.

## Syntax

```fuseql
'term'
'term1 term2'
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `'term'` | Yes | A single-quoted word or space-separated words. Each word is matched as a whole lower-cased token from the Lucene index. When multiple words are given, **all** must appear somewhere in the log line (logical AND, any order). This is not a phrase search. |

## Examples

### Single-word token search

Return all logs that contain the whole token `error`.

```fuseql
'error' | count by source
```

**Validated output:**

| source | _count |
|---|---|
| grafana | 1,361,209 |
| rum-query-service | 2,645 |
| pinot-broker | 659 |
| logs-query-service | 432 |
| … | … |

**Total: ~22.9 million log lines** across 44 sources (1-hour window).

### Multi-word token search (AND, any order)

Return all logs that contain **both** `logger` and `error` — each word matched independently anywhere in the line.

```fuseql
'logger error' | count by source
```

**Validated output:**

| source | _count |
|---|---|
| grafana | 1,361,193 |
| kf-performance-log | 10 |
| logs-query-service | … |

**Total: ~1.37 million log lines** — a stricter result than either word alone (`'error'` = 22.9M, `'logger'` = 2.1M).

### Order independence

The same query with words reversed returns **identical results**, confirming that word order is irrelevant:

```fuseql
'error logger' | count by source
```

**Validates the same ~1.37 million rows** as `'logger error'`.

### Phrase search comparison (grep)

To require the words adjacent in a specific order, use grep instead:

```fuseql
"logger error" | count by source
```

**Validated output:** 6 rows (only log lines containing the literal sequence `logger error`).

```fuseql
"error logger" | count by source
```

**Validated output:** 2 rows (only log lines containing the literal sequence `error logger`).

This confirms term search and grep behave very differently for multi-word queries.

## API call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <sa-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"'\''logger error'\'' | count by source\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Limitations

- **Not a phrase search.** `'word1 word2'` does not require the words to appear adjacent or in order. Use grep (`"word1 word2"`) for phrase matching.
- **No partial-token matching.** `'schedule'` will not match the token `com.example.scheduler.Job` — the entire dot-separated string is a single token.
- **Stop words are silently dropped.** Common words such as `is`, `not`, `in`, `the`, `and`, `or` are removed before lookup. `'is not valid'` reduces to `'valid'` only.
- **No wildcard support.** Use grep for patterns like `err*`.
- **Case-insensitive only.** Token lookup is always lowercase. For case-sensitive matching, use grep.
- **Not supported on view queries** (`_view=…`).

## Notes

- Token matching is the fastest full-text search method — it uses the inverted index directly without scanning raw log bodies.
- Use it when you know the exact whole word(s) and position does not matter.
- When multiple tokens are listed (`'word1 word2'`), **all** tokens must appear in the log line in **any order** — this is a logical AND, not a phrase search.
- For whole-line scans, substring matches, or wildcard patterns, use the grep operator (`"expression"`).
- To match *any* of several words (OR), use separate term searches connected with the OR operator or multiple filters.
