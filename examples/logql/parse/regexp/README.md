# regexp

Extracts fields using an RE2 regular expression with named capture groups: each `(?P<name>...)` group becomes a label. Reach for `regexp` when the line shape is too irregular for the `pattern` parser — optional fields, repeated separators, or matches that anchor mid-line.

## Syntax

```
| regexp "<re2-expression>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<re2-expression>` | Required | An RE2 regular expression containing at least one named capture group `(?P<name>...)`. Unnamed groups are not extracted. |

## Example

Extract the HTTP method, path, and status code from nginx access-log lines, then keep successful requests only.

<!-- validation: kind=range minutes=3 -->
```logql
{source="nginx"}
| regexp "\"(?P<method>[A-Z]+) (?P<path>[^ ]+) [^\"]*\" (?P<status>[0-9]+)"
| status="200"
```

**Expected output:**

```
10.2.134.241 - - [04/Jul/2026:15:41:27 +0000] "POST /ingester/otlp/v1/logs HTTP/1.1" 200 2 "-" "OpenTelemetry  ...
10.2.140.116 - - [04/Jul/2026:15:41:27 +0000] "POST /ingester/v1/fluent_bit HTTP/1.1" 200 0 "-" "Fluent-Bit" 1 ...
10.2.140.70 - - [04/Jul/2026:15:41:27 +0000] "POST /ingester/v1/fluent_bit HTTP/1.1" 200 0 "-" "Fluent-Bit" 69 ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} | regexp "\"(?P<method>[A-Z]+) (?P<path>[^ ]+) [^\"]*\" (?P<status>[0-9]+)" | status="200"' \
  --data-urlencode "start=$(date -u -v-3M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Backslashes must be doubled inside double-quoted strings (`\\d`); character classes such as `[0-9]` avoid the escaping entirely.
- RE2 does not support look-ahead or back-references.
