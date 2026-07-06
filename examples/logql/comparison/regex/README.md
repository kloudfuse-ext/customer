# Regex match (=~)

Selects log streams whose label value matches an RE2 regular expression. The expression is fully anchored: it must match the entire label value, so `nginx.*` matches `nginx` and `nginx-fips` but `gin` matches nothing. Use it to select a family of related streams in one query.

## Syntax

```
{<label>=~"<regex>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The stream label to test. |
| `<regex>` | Required | An RE2 regular expression. The match is anchored at both ends of the label value. |

## Example

Select logs from every nginx variant at once — both the `nginx` and `nginx-fips` ingress controllers match the expression.

<!-- validation: kind=range minutes=10 -->
```logql
{source=~"nginx.*"}
```

**Expected output:**

```
10.20.10.114 - - [04/Jul/2026:15:38:10 +0000] "POST /ingester/api/v1/filebeat/_bulk HTTP/1.1" 200 4854 "-" "Elastic-file ...
10.20.15.199 - - [04/Jul/2026:15:38:10 +0000] "POST /ingester/otlp/v1/logs HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
10.20.15.230 - - [04/Jul/2026:15:38:10 +0000] "POST /ingester/otlp/metrics HTTP/2.0" 200 2 "-" "ZSOS 42  OpenTelemetry C ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source=~"nginx.*"}' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- RE2 does not support look-ahead or look-behind assertions.
- Alternation picks specific streams: `{source=~"nginx|grafana|zookeeper"}`.
