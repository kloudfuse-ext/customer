# split

Splits a string field on a delimiter and extracts sub-fields by position or index. Use `split` to parse delimited log formats such as CSV, tab-separated values, or colon-delimited strings.

## Syntax

```fuseql
| split <field> extract <A>, <B>, ...
| split <field> extract 0 as <A>, 1 as <B>, ...
| split <field> extract <A>, <B>, 4 as <E>, <F>
| split <field> delim='<d>' escape='<e>' quote='<q>' extract <A>, <B>, ...
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<field>` | Required | The string field to split. Use `_kf_msg` to split the raw log line. |
| `extract <aliases>` | Required | Positional aliases (`<A>, <B>`) or index-based aliases (`0 as <A>, 1 as <B>`). Use `_` to skip a position. |
| `delim='<d>'` | Optional | Delimiter character. Defaults to `,`. |
| `escape='<e>'` | Optional | Escape character. Defaults to `\`. |
| `quote='<q>'` | Optional | Quote character. Defaults to `"`. |

## Example

Split a comma-separated log field and extract the timestamp, level, and message.

```fuseql
source="csv-app"
| split _kf_msg extract 0 as log_timestamp, 1 as log_level, 2 as log_message
| count as events by log_level
```

**Expected output:**

| log_level | events |
|---|---|
| ERROR | 4,821 |
| WARN | 18,204 |
| INFO | 843,291 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"csv-app\\\" | split _kf_msg extract 0 as log_timestamp, 1 as log_level, 2 as log_message | count as events by log_level\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Positions are zero-indexed: the first sub-field is index `0`.
- Use `_` (underscore) to skip a position you do not need.
- The three custom characters (delimiter, escape, quote) must all be distinct single characters.
- For more complex extraction, combine `split` with `parse regex`.
