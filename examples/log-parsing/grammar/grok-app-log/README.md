# Grok: timestamp, level, and message

The `grok` example from the Kloudfuse docs (Data Management -> Log Parsing ->
Configuration, "Grok patterns"), scoped to one source.

## Pipeline config

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - parser:
          grok:
            args:
              - patterns:
                  - '%{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} %{GREEDYDATA:msg}'
            conditions:
              - matcher: "#source"
                value: "nginx"
                op: "=="
```

## Sample line

```
2024-01-16T10:30:00Z ERROR Connection failed
```

## Expected facets

| Facet | Value |
|---|---|
| `ts` | `2024-01-16T10:30:00Z` |
| `level` | `ERROR` |
| `msg` | `Connection failed` |

## Validation

Requires `pip install pygrok` (the tester wraps it; see `../../grok_tester.py`).

<!-- validation: kind=grok -->
```json
{
  "patterns": ["%{TIMESTAMP_ISO8601:ts} %{LOGLEVEL:level} %{GREEDYDATA:msg}"],
  "line": "2024-01-16T10:30:00Z ERROR Connection failed",
  "expected": {
    "ts": "2024-01-16T10:30:00Z",
    "level": "ERROR",
    "msg": "Connection failed"
  }
}
```
