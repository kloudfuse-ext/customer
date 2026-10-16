# grammar: grok

A named-regex tokenizer for plain-text log lines — more flexible than
`dissect` for lines whose shape varies, at the cost of being slower and
easier to write inefficiently. Uses the same pattern library and syntax as
the Logstash grok filter.

## Syntax

```yaml
- parser:
    grok:
      args:
        - patterns:
            - '<grok-pattern>'
        - field: "<field>"    # optional; defaults to the message
      conditions:              # optional, recommended
        - matcher: "#source"
          value: "<source-name>"
          op: "=="
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `patterns` | Yes | A list of grok patterns; the message is matched against the combination. Named captures (`%{PATTERN:field}`) become facets. |
| `field` | No | Which field to match against. Defaults to the log message. |

## Example

Extract a timestamp, level, and free-text message from a plain-text
application log line, using the built-in `TIMESTAMP_ISO8601` and `LOGLEVEL`
patterns.

<!-- validation: expect=facet:level=ERROR -->
```yaml
- parser:
    grok:
      args:
        - patterns:
            - '%{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} %{GREEDYDATA:msg}'
      conditions:
        - matcher: "#source"
          value: "checkout-api"
          op: "=="
```
```json
{"message": "2026-07-04T15:37:52.411Z ERROR payment gateway timeout after 30000ms", "ddsource": "checkout-api"}
```

**Expected output:** `result.facets` includes `ts: 2026-07-04T15:37:52.411Z`,
`level: ERROR`, and `msg: payment gateway timeout after 30000ms`.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- Reusable named patterns (referenced by name inside another pattern) can be defined once under a top-level `parser_patterns` key and reused across multiple `grok`/`dissect` functions — see the Log Parsing Configuration docs' Grammar section.
- Prefer `dissect` when a line's structure is fixed; reach for `grok` when it varies enough that a positional tokenizer can't express it.
