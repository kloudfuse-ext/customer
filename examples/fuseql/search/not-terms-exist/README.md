# !term (not terms exist)

Token exclusion filter operator. Excludes log lines whose message body contains all of the specified whole tokens. This is the logical complement of the term search (`'term'`) operator — it queries the Lucene inverted index and excludes any line where every specified token is present as a whole word.

> **Important — multi-word excludes only when ALL tokens are present.**
> `!'word1 word2'` excludes a log line only if *both* tokens appear somewhere in the line. A line containing only `word1` (but not `word2`) is **not** excluded — it is included in results. This is the De Morgan complement of the AND logic used by `'word1 word2'`.

## Syntax

```fuseql
!'term'
!'term1 term2'
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `!'term'` | Yes | A negated single-quoted word or space-separated words. Each word is matched as a whole lower-cased token. A log line is excluded only if **all** listed tokens are present as whole words. A line missing any one of the tokens is included in results. |

## Examples

### Single-word exclusion

Return all logs that do **not** contain the token `error`.

```fuseql
!'error' | count by source
```

**Validated output (top sources):**

| source | _count |
|---|---|
| pinot-server | ~66,700,000 |
| zookeeper | 108,004 |
| pinot-gclog-broker | 21,210 |
| … | … |

**Total: ~185 million log lines** — logs where `error` does not appear as a whole token (1-hour window).

### Multi-word exclusion (AND complement)

Exclude logs that contain **both** `logger` and `error` (lines with only one of the two tokens are kept).

```fuseql
!'logger error' | count by source
```

**Validated output:**

**Total: ~207 million log lines** — larger than `!'error'` (185M) because lines containing only `logger` (without `error`) are now included in the result.

### Why `!'logger error'` returns more rows than `!'error'`

| Query | Logic | Result |
|---|---|---|
| `!'error'` | Exclude lines with the `error` token | ~185M rows |
| `!'logger error'` | Exclude lines with **both** `logger` AND `error` | ~207M rows |

The difference (~22M rows) represents log lines that contain the `error` token but **not** the `logger` token — those lines are excluded by `!'error'` but included by `!'logger error'`.

## API call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <sa-token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"!'\''error'\'' | count by source\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `!'term'` matches whole tokens only — it will not exclude a token that merely contains the string as a substring. For example, `!'health'` excludes lines where `health` is a complete token (e.g. from `level=health`) but does not exclude lines where the text appears only as part of a larger token such as `healthcheck` (no boundary after `health`).
- To exclude substring matches regardless of token boundaries, use the not-grep operator (`!"health"`).
- When multiple tokens are listed (`!'word1 word2'`), a line is excluded only if it contains **all** listed tokens. A line missing any token is included. This is the complement of the AND logic in `'word1 word2'`.
- Matching is case-insensitive: `!'ERROR'` and `!'error'` produce identical results.
