# Line contains (|=)

Keeps log lines that contain the given string anywhere in the line. This is the LogQL equivalent of `grep`: fast, case-sensitive, and the workhorse of interactive log exploration. Chain several filters to narrow results step by step.

## Syntax

```
{<selector>} |= "<string>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | The substring to search for. Matching is case-sensitive; no regex interpretation is applied. |

## Example

Find all `POST` requests handled by the nginx ingress controller.

<!-- validation: kind=range minutes=10 -->
```logql
{source="nginx"} |= "POST"
```

**Expected output:**

```
10.20.15.233 - - [04/Jul/2026:15:38:16 +0000] "POST /ingester/otlp/v1/logs HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
10.20.15.210 - - [04/Jul/2026:15:38:16 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
10.20.15.217 - - [04/Jul/2026:15:38:16 +0000] "POST /ingester/otlp/v1/logs HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} |= "POST"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Line filters run before parsers and are heavily optimized — put them as early and as selective as possible.
- For case-insensitive matching use the regex filter with the `(?i)` flag: `|~ "(?i)post"`.
