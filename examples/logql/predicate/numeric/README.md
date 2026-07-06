# Numeric comparison

Compares a label value as a number using `==`, `!=`, `>`, `>=`, `<`, or `<=`. The label's string value is converted to a number for the comparison; lines whose value does not parse get the `__error__` label instead of matching.

## Syntax

```
| <label> >= <number>    (also ==, !=, >, <, <=)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | A label whose value is numeric text, typically extracted by a parser. |
| `<number>` | Required | An unquoted integer or float literal. |

## Example

Extract the HTTP status code from nginx access logs and keep only client and server errors (status 400 and above).

<!-- validation: kind=range minutes=3 -->
```logql
{source="nginx"}
| regexp "\" (?P<status>[0-9]{3}) (?P<resp_bytes>[0-9]+)"
| status >= 400
```

**Expected output:**

```
10.20.15.214 - - [04/Jul/2026:15:41:41 +0000] "POST /ingester/otlp/v1/logs HTTP/2.0" 403 0 "-" "OpenTelemetry  ...
10.2.130.201 - - [04/Jul/2026:15:41:40 +0000] "POST /ingester/otlp/v1/logs HTTP/1.1" 403 0 "-" "OpenTelemetry  ...
10.2.135.177 - zd3150 [04/Jul/2026:15:41:40 +0000] "POST /write HTTP/1.1" 403 0 "-" "vmagent" 527 0.001 [kfuse ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} | regexp "\" (?P<status>[0-9]{3}) (?P<resp_bytes>[0-9]+)" | status >= 400' \
  --data-urlencode "start=$(date -u -v-3M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Use `==` for numeric equality; a single `=` compares as a string.
