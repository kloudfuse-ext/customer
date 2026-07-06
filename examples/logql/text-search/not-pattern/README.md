# Pattern not match (!>)

Discards log lines that match a pattern expression. Use it to exclude a well-known line shape — such as all `GET` requests — while keeping everything else.

## Syntax

```
{<selector>} !> "<pattern>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<pattern>` | Required | A pattern expression; lines that fully match are removed. `<_>` matches any text. |

## Example

Drop all `GET` requests from the nginx access log, keeping POST, PUT, DELETE, and other methods.

<!-- validation: kind=range minutes=10 -->
```logql
{source="nginx"} !> "<_>\"GET <_>"
```

**Expected output:**

```
10.20.15.218 - - [04/Jul/2026:15:38:36 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
10.20.15.211 - - [04/Jul/2026:15:38:36 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
10.20.15.234 - - [04/Jul/2026:15:38:36 +0000] "POST /ingester/otlp/v1/logs HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} !> "<_>\"GET <_>"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Pattern filters are useful for excluding high-volume line shapes cheaply, before any parser runs.
