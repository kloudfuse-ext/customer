# pattern

Extracts fields by matching the line against a template made of literal text and capture placeholders: `<name>` captures text into a label, `<_>` matches and discards. The pattern parser is faster and far easier to read than an equivalent regular expression, and is the recommended parser for fixed-shape plain-text formats such as nginx access logs.

## Syntax

```
| pattern "<pattern-expression>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<pattern-expression>` | Required | Literal text with `<name>` captures and `<_>` wildcards. Literals must match the line exactly; two captures cannot be adjacent. |

## Example

Parse the leading fields of each access-log entry from the `delegate` service — client IP, timestamp, method, path, status, and response bytes — then keep only `GET` requests.

<!-- validation: kind=range minutes=10 -->
```logql
{source="delegate"}
| pattern "<client_ip> - - [<ts>] \"<method> <path> <_>\" <status> <bytes> <_>"
| method="GET"
```

**Expected output:**

```
10.16.4.33 - - [04/Jul/2026:15:48:08 +0000] "GET /api/metrics HTTP/1.1" 200 463 "-" "Datadog Agent/7.53.0" 1
10.16.4.33 - - [04/Jul/2026:15:48:23 +0000] "GET /api/metrics HTTP/1.1" 200 463 "-" "Datadog Agent/7.53.0" 0
10.16.4.33 - - [04/Jul/2026:15:48:39 +0000] "GET /api/metrics HTTP/1.1" 200 463 "-" "Datadog Agent/7.53.0" 0
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="delegate"} | pattern "<client_ip> - - [<ts>] \"<method> <path> <_>\" <status> <bytes> <_>" | method="GET"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Escape double quotes that are part of the log line as `\"` inside the double-quoted pattern.
- The pattern must match from the start of the line; trailing content is covered by the final `<_>`.
