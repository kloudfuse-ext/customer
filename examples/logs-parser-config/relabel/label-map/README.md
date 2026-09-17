# relabel: label_map

Renames every label whose *name* (not value) matches `regex`, replacing the
matched portion with `replacement`. Unlike the other actions, `label_map`
operates on label names and ignores `sourceLabels`/`targetLabel` entirely.

## Syntax

```yaml
- relabel:
    args:
      - action: "label_map"
      - regex: "<regex-matched-against-label-names>"
      - replacement: "<replacement>"
    conditions:    # optional
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `regex` | Yes | Pattern matched against each existing label's *name*. |
| `replacement` | Yes | New name for any label whose name matches, using standard regex replacement (capture groups supported). |

## Example

Rename the `source` label to `service_name` to match a downstream naming
convention.

<!-- validation: expect=tag:service_name=checkout-api -->
```yaml
- relabel:
    args:
      - action: "label_map"
      - regex: "^source$"
      - replacement: "service_name"
```
```json
{"message": "GET /health 200 12ms", "ddsource": "checkout-api"}
```

**Expected output:** `result.tags` includes `"service_name": "checkout-api"`
and no longer includes `source`.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- `label_keep` and `label_drop` (not shown here) use the same name-matching mechanics — `label_keep` removes every label whose name does *not* match `regex`, `label_drop` removes every label whose name does.
- Place `label_map` after whatever produced the label you're renaming — function order in the `config` list is what determines this, not a fixed pipeline stage.
