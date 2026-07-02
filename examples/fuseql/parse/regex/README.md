# parse regex

Extracts fields from log lines using regular expressions with named capture groups. Use `parse regex` when log formats are complex or variable — for example, when the field is not surrounded by fixed anchor strings, or when you need to match multiple alternative formats.

## Syntax

```fuseql
| parse regex "<pattern>(?P<field_name><expression>)<pattern>"
| parse regex "<pattern>(?P<field_name><expression>)<pattern>" nodrop
| parse regex [field=<source_field>] "<pattern>(?P<field_name><expression>)<pattern>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `"<regex>"` | Required | A regular expression with one or more named capture groups `(?P<name>pattern)`. Each group becomes an output field. |
| `nodrop` | Optional | Retain non-matching lines with null output fields. |
| `field=<source_field>` | Optional | Apply the regex to a specific extracted field rather than the full log line. |

## Example

Extract the HTTP method and URL path from nginx log lines.

```fuseql
source="nginx"
| parse regex "\"(?P<method>GET|POST|PUT|DELETE|OPTIONS) (?P<path>[^ ]+)"
| count as requests by method
```

**Expected output:**

| method | requests |
|---|---|
| GET | 1,412,840 |
| POST | 198,233 |
| OPTIONS | 257,234 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse regex \\\"\\\\\\\"(?P<method>GET|POST|PUT|DELETE|OPTIONS) (?P<path>[^ ]+)\\\"\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Named capture groups use Python-style syntax: `(?P<name>pattern)`. Each group name becomes a new field.
- For simpler patterns with fixed delimiters, `parse anchor` is easier to write and read.
- `nodrop` is important when the regex matches only a subset of log lines.
