# Line does not contain (!=)

Discards log lines that contain the given string. Use it to peel away known noise — health checks, expected traffic, or messages you have already investigated — so the unexpected lines stand out.

## Syntax

```
{<selector>} != "<string>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Required | Lines containing this substring are removed from the result. |

## Example

Show `POST` traffic while hiding the high-volume log-ingestion endpoint, leaving the less common POST routes.

<!-- validation: kind=range minutes=10 -->
```logql
{source="nginx"} |= "POST" != "/ingester/otlp/v1/logs"
```

**Expected output:**

```
10.20.15.192 - - [04/Jul/2026:15:38:20 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
10.20.15.211 - - [04/Jul/2026:15:38:20 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
10.20.15.200 - - [04/Jul/2026:15:38:20 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"} |= "POST" != "/ingester/otlp/v1/logs"' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Inside a pipeline `!=` is a line filter; inside a stream selector `{...}` the same symbol is a label matcher. The position determines the meaning.
