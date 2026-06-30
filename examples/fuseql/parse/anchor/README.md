# parse anchor

Extracts a substring from a log line by specifying fixed start and stop anchor strings with a `*` wildcard placeholder. Use `parse anchor` for predictable, delimited log formats where the value always appears between two known literal strings.

## Syntax

```fuseql
| parse "<start_anchor>*<stop_anchor>" as <field>
| parse "<start_anchor>*<stop_anchor>" as <field> nodrop
| parse [field=<source_field>] "<start_anchor>*<stop_anchor>" as <field>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `"<start>*<stop>"` | Required | Pattern with exactly one `*` per extracted field. Text before `*` is the start anchor; after is the stop anchor. |
| `as <field>` | Required | Name of the output field for the captured value. Multiple wildcards extract multiple fields. |
| `nodrop` | Optional | Retain non-matching lines with null output fields. By default, non-matching lines are dropped. |
| `field=<source_field>` | Optional | Parse from a specific field rather than the full log line. |

## Example

Extract IP, method, URL, status, and bytes from nginx access log lines.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
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
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | count as requests by method\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Each `*` in the pattern captures one field. Supply one alias per `*` in the `as` clause, separated by commas.
- For complex patterns, use `parse regex` with named capture groups.
- `nodrop` is essential when the pattern matches only a subset of log lines.
