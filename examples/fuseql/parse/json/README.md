# parse json

Extracts one or more fields from JSON-formatted log lines using key names or JSONPath expressions. Eliminates the need for regex patterns when logs are already structured as JSON.

## Syntax

```fuseql
| json "<key>"[, "<key2>", ...] [as <alias> ...]
| json "<key>"[, "<key2>", ...] [as <alias>] [nodrop]
| json [field=<source_field>] "<key>"[, "<key2>", ...] [as <alias> ...]
| json "<parent>.[*].<child>" multi type=["string" | "int" | "double"]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `"<key>"` | Required | A top-level key name or dotted JSONPath (e.g., `"user.details.age"`). Multiple keys are comma-separated. |
| `as <alias>` | Optional | Renames the extracted field. Supply one alias per key in order. |
| `nodrop` | Optional | Retain log lines missing the key (output field will be null). |
| `field=<source_field>` | Optional | Parse from a specific field rather than the full log line. |
| `multi type=` | Optional | Used with array paths (`.[*].`) to extract array elements. Specify `"string"`, `"int"`, or `"double"`. |

## Example

Extract `method` and `status` from JSON-formatted application logs and count by both fields.

```fuseql
source="app-json"
| json "method", "status" as http_method, http_status
| count as requests by http_method, http_status
```

**Expected output:**

| http_method | http_status | requests |
|---|---|---|
| GET | 200 | 842,301 |
| POST | 201 | 97,443 |
| GET | 404 | 12,087 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"app-json\\\" | json \\\"method\\\", \\\"status\\\" as http_method, http_status | count as requests by http_method, http_status\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- Use dotted paths to reach nested fields: `json "user.details.age" as age`.
- To extract array elements: `json "users.[*].score" multi type="int"`.
- `nodrop` is essential when the JSON key is present in only some log lines.
- After extraction, FuseQL coerces string-typed numeric values automatically in aggregation contexts.
