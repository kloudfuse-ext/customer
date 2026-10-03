# Transform: promote a facet to a label

The `facet_to_label_map` example from the Kloudfuse docs (Data Management ->
Log Parsing -> Configuration, "Transform and fingerprinting") — promotes a
facet extracted earlier in the pipeline (by Grammar) into an always-indexed
label. `transform` runs the same action engine as `relabel`, but always
executes after Grammar/JSON auto-parsing regardless of where you place it in
the `config` list — `relabel`, by contrast, always runs *before* any facet
extraction, so it can't be used for this (see the note in
`../drop-healthcheck-lines/README.md`).

## Pipeline config

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      ...
      - transform:
          args:
            - action: "facet_to_label_map"
            - sourceLabels: "@eventSource"
            - targetLabel: "source"
          conditions:
            - matcher: "#source"
              op: "=="
              value: "awsLogSource"
```

## Before / after

| | Facets | Labels |
|---|---|---|
| Before | `{"eventSource": "awsLogSource"}` | `{}` |
| After | `{"eventSource": "awsLogSource"}` | `{"source": "awsLogSource"}` |

`facet_to_label_map` copies the value — it does not remove the source facet,
so both the facet and the new label exist afterward.

## Validation

<!-- validation: kind=relabel -->
```json
{
  "args": {"action": "facet_to_label_map", "sourceLabels": "@eventSource", "targetLabel": "source"},
  "input": {"facets": {"eventSource": "awsLogSource"}, "labels": {}},
  "expected": {"facets": {"eventSource": "awsLogSource"}, "labels": {"source": "awsLogSource"}}
}
```
