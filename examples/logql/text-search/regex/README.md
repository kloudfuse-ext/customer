# Line regex match (|~)

Keeps log lines that match an RE2 regular expression. Unlike stream-selector regex matchers, line filter expressions are not anchored — the pattern can match anywhere in the line. Use it when a plain substring is not expressive enough.

## Syntax

```
{<selector>} |~ "<regex>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<regex>` | Required | An RE2 regular expression, unanchored. Escape backslashes inside the double-quoted string (write `\\d` for a digit class) or use backticks to avoid escaping. |

## Example

Match lines for either mutating HTTP method with one alternation.

<!-- validation: kind=range minutes=10 -->
```logql
{source="nginx"} |~ "POST|PUT"
```

**Expected output:**

```
10.20.10.105 - - [04/Jul/2026:15:38:27 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "OpenTelemetry Collector  ...
10.20.15.212 - - [04/Jul/2026:15:38:27 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "OpenTelemetry Collector  ...
10.20.10.120 - - [04/Jul/2026:15:38:27 +0000] "POST /ingester/otlp/v1/logs HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} |~ "POST|PUT"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Prefer `|=` for plain substrings — it is cheaper than a regex.
- Add `(?i)` at the start of the expression for case-insensitive matching.
