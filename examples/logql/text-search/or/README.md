# Or (or)

Chains multiple values onto a single line filter so that a line matches if any value matches. The `or` keyword applies to all line filter types — contains, regex, and pattern — and keeps queries readable when matching several alternatives.

## Syntax

```
{<selector>} |= "<string1>" or "<string2>" [or "<string3>" ...]
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<stringN>` | Required | Two or more filter values. The line is kept (or dropped, for negated filters) when any value matches. |

## Example

Keep nginx lines containing either mutating HTTP method. The result is equivalent to the regex filter `|~ "POST|PUT"` but uses cheaper substring matching.

<!-- validation: kind=range minutes=10 -->
```logql
{source="nginx"} |= "POST" or "PUT"
```

**Expected output:**

```
10.20.0.17 - - [04/Jul/2026:15:38:42 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry Col ...
10.150.25.1 - - [04/Jul/2026:15:38:42 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry Co ...
10.20.15.213 - - [04/Jul/2026:15:38:42 +0000] "POST /ingester/otlp/v1/logs HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} |= "POST" or "PUT"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- For negated filters the logic inverts naturally: `!= "a" or "b"` drops lines containing `a` and lines containing `b`.
