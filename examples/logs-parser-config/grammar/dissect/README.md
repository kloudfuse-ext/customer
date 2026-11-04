# grammar: dissect

A text tokenizer for plain-text log lines: literal delimiter text separates
`%{fieldname}` captures. Faster and more predictable than a regex-based grok
pattern when a line's shape is fixed, at the cost of being less flexible
about variation in that shape.

## Syntax

```yaml
- parser:
    dissect:
      args:
        - tokenizer: '<tokenizer-pattern>'
      conditions:    # optional, recommended — scope to the source this pattern is for
        - matcher: "#source"
          value: "<source-name>"
          op: "=="
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `tokenizer` | Yes | The dissect pattern. `%{field}` captures; a prefix changes behavior — `%{?a}` matches without capturing, `%{+b}` appends to a previous capture, `%{&c}` references an earlier capture. Bracket notation `%{[field][subfield]}` nests the field name. |

## Example

Extract structured fields from an Nginx-style access log line.

<!-- validation: expect=facet:responseCode=503 -->
```yaml
- parser:
    dissect:
      args:
        - tokenizer: '%{sourceIp} - - [%{timestamp}] "%{requestMethod} %{uri} %{_}" %{responseCode} %{contentLength}'
      conditions:
        - matcher: "#source"
          value: "nginx"
          op: "=="
```
```json
{"message": "10.12.0.35 - - [26/May/2021:18:59:10 +0000] \"GET /unavailable HTTP/1.1\" 503 21", "ddsource": "nginx"}
```

**Expected output:** `result.facets` includes `sourceIp: 10.12.0.35`,
`requestMethod: GET`, `uri: /unavailable`, `responseCode: 503`, and
`contentLength: 21`.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- `%{_}` is the conventional name for a capture you want positionally but don't need to keep — here it swallows the HTTP version.
- Test a tokenizer against real sample lines with a dissect debugger before deploying, or use `test_pipeline.py`/`validate_examples.py` directly against a captured payload.
- Scope with `conditions` on `#source` (as above) — an unscoped tokenizer runs against every log line the pipeline sees, including ones it wasn't written for.
