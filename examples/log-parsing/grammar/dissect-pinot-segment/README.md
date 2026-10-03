# Dissect: structured prefix + level + segment name

A compact dissect pattern that extracts a level and a dynamic segment name from
a line that starts with a fixed, bracketed template — the first example from
the Kloudfuse docs (Data Management -> Log Parsing -> Configuration, "Dissect
patterns"), scoped with a `contains` condition instead of an equality match.

## Pipeline config

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - parser:
          dissect:
            args:
              - tokenizer: '%{timestamp} %{level} [LLRealtimeSegmentDataManager_%{segment_name}]'
            conditions:
              - matcher: "%kf_msg"
                value: "LLRealtimeSegmentDataManager_"
                op: "contains"
```

## Sample line

```
2024-01-16T10:30:00Z INFO [LLRealtimeSegmentDataManager_table__0__1__20240116T1030Z]
```

## Expected facets

| Facet | Value |
|---|---|
| `timestamp` | `2024-01-16T10:30:00Z` |
| `level` | `INFO` |
| `segment_name` | `table__0__1__20240116T1030Z` |

The trailing `]` in the tokenizer is a literal delimiter, not part of the
capture — dissect matches it against the line's closing bracket and excludes
it from `segment_name`, the same way the opening `[` and the literal prefix
`LLRealtimeSegmentDataManager_` are excluded.

## Validation

<!-- validation: kind=dissect -->
```json
{
  "tokenizer": "%{timestamp} %{level} [LLRealtimeSegmentDataManager_%{segment_name}]",
  "line": "2024-01-16T10:30:00Z INFO [LLRealtimeSegmentDataManager_table__0__1__20240116T1030Z]",
  "expected": {
    "timestamp": "2024-01-16T10:30:00Z",
    "level": "INFO",
    "segment_name": "table__0__1__20240116T1030Z"
  }
}
```
