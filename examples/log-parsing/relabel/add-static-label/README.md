# Relabel: add a static label

The `replace` example from the Kloudfuse docs (Data Management -> Log Parsing
-> Configuration, "Relabel") — tags every log line it runs against with a
fixed `env` label. `regex: ".*"` always matches, so `replace` always fires.

## Pipeline config

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - relabel:
          args:
            - action: "replace"
            - regex: ".*"
            - replacement: "production"
            - targetLabel: "env"
```

## Before / after

| | Labels |
|---|---|
| Before | `{}` |
| After | `{"env": "production"}` |

## Validation

<!-- validation: kind=relabel -->
```json
{
  "args": {"action": "replace", "regex": ".*", "replacement": "production", "targetLabel": "env"},
  "input": {"facets": {}, "labels": {}},
  "expected": {"facets": {}, "labels": {"env": "production"}}
}
```
