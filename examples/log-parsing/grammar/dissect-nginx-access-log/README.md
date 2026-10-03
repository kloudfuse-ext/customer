# Dissect: nginx access log

The worked example from the Kloudfuse docs (Data Management -> Log Parsing ->
Configuration, "Worked example: deriving a facet with a tokenizer"), scoped to
one source with a `conditions` matcher.

## Pipeline config

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - parser:
          dissect:
            args:
              - tokenizer: '%{sourceIp} - - [%{timestamp}] "%{requestMethod} %{uri} %{_}" %{responseCode} %{contentLength}'
            conditions:
              - matcher: "#source"
                value: "nginx"
                op: "=="
```

## Sample line

```
10.12.0.35 - - [26/May/2021:18:59:10 +0000] "GET /unavailable HTTP/1.1" 503 21 "-" "hey/0.0.1"
```

## Expected facets

| Facet | Value |
|---|---|
| `sourceIp` | `10.12.0.35` |
| `timestamp` | `26/May/2021:18:59:10 +0000` |
| `requestMethod` | `GET` |
| `uri` | `/unavailable` |
| `_` | `HTTP/1.1` |
| `responseCode` | `503` |
| `contentLength` | `21` |

Note: `%{contentLength}` has no literal delimiter after it, but it does
*not* capture the rest of the line — confirmed against a running
logs-parser's `/pipeline/test-function` API, a trailing field with nothing
after it in the pattern stops at the next whitespace. The referer and
user-agent quoted after the byte count (`"-" "hey/0.0.1"`) are left
unconsumed, not appended to `contentLength`.

## Validation

<!-- validation: kind=dissect -->
```json
{
  "tokenizer": "%{sourceIp} - - [%{timestamp}] \"%{requestMethod} %{uri} %{_}\" %{responseCode} %{contentLength}",
  "line": "10.12.0.35 - - [26/May/2021:18:59:10 +0000] \"GET /unavailable HTTP/1.1\" 503 21 \"-\" \"hey/0.0.1\"",
  "expected": {
    "sourceIp": "10.12.0.35",
    "timestamp": "26/May/2021:18:59:10 +0000",
    "requestMethod": "GET",
    "uri": "/unavailable",
    "_": "HTTP/1.1",
    "responseCode": "503",
    "contentLength": "21"
  }
}
```
