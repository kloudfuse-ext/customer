# relabel: facet_to_label_map (a.k.a. Transform)

Copies the value of a facet into a label. With `regex`/`replacement` set, it
transforms the value on the way; with no `regex`, it copies the facet value
as-is. This is the action almost always written as `transform` rather than
`relabel` — see Notes — because it's typically placed *after* the grammar
step that extracted the facet being promoted.

## Syntax

```yaml
- transform:                          # or `relabel` — same engine, same action
    args:
      - action: "facet_to_label_map"
      - sourceLabels: "@<facet-name>"
      - targetLabel: "<label-name>"
      - regex: "<regex>"              # optional
      - replacement: "<replacement>"  # optional, requires regex
    conditions:                       # optional
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `sourceLabels` | Yes | The facet to promote, `@`-prefixed. |
| `targetLabel` | Yes | The label to write. |
| `regex` | No | If set, only promotes when the facet value matches; `replacement` transforms it. If omitted, the facet value is copied as-is. |

## Example

Promote a JSON message's `eventSource` facet to a first-class `source` label,
so it's filterable the same way as any other label.

<!-- validation: expect=tag:source=aws-cloudtrail -->
```yaml
- transform:
    args:
      - action: "facet_to_label_map"
      - sourceLabels: "@eventSource"
      - targetLabel: "source"
```
```json
{"message": "{\"eventSource\": \"aws-cloudtrail\", \"eventName\": \"ConsoleLogin\"}", "ddsource": "unknown"}
```

**Expected output:** `result.tags` includes `"source": "aws-cloudtrail"`,
overriding whatever `ddsource` would otherwise have produced.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- `relabel` and `transform` are the *same* function class (`Relabeler`), registered under two different config keys. Which name you use is a convention for readability — `relabel` early in the list, `transform` late — not a functional difference.
- Renaming the label written here to `source` and scoping it with `conditions` (for example, only when `#source == "awsLogSource"`) is the pattern used to override the default source-derived label for a specific integration.
