# addFacet

Adds a facet with a fixed value — useful for tagging every log a pipeline
function processes with a constant, independent of anything in the message
itself (a config version, a pipeline identifier, and so on).

## Syntax

```yaml
- addFacet:
    args:
      - name: "<facet-name>"
      - value: "<facet-value>"
      - replace: <true|false>    # optional; default true
    conditions:                  # optional
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `name` | Yes | The facet to set. |
| `value` | Yes | The fixed value to write. |
| `replace` | No | Whether to overwrite an existing facet of the same name. Default `true`. |

## Example

Tag every log processed by this rule with the pipeline config version that
produced it, scoped to one source.

<!-- validation: expect=manual -->
```yaml
- addFacet:
    args:
      - name: "pipeline_version"
      - value: "3"
    conditions:
      - matcher: "#source"
        value: "checkout-api"
        op: "=="
```
```json
{"message": "GET /health 200 12ms", "ddsource": "checkout-api"}
```

**Expected output:** `result.facets` includes `pipeline_version: 3`.

**Unresolved discrepancy, tested against a live `logs-parser`:** this facet
did not appear in the response — tried with and without `conditions`, with
and without an explicit `replace`, and overwriting an existing facet name
(`_number_0`) instead of a new one, all through `/pipeline/test-function`.
The last case showed *some* interaction (the built-in numeric-facet
extractor renamed itself to `_number_0_1` to avoid a collision), but the
value `addFacet` wrote was never visible in the final response either way.
By contrast, `relabel`, `transform`, `setLogLevel`, and `logFmt` all behaved
exactly as documented through the same endpoint with the same YAML shape.
This is marked `expect=manual` rather than asserted as broken — it may be a
`/pipeline/test-function`-specific quirk (see the file-level docstring in
`validate_examples.py` for a confirmed, related timing issue with this
endpoint) rather than a problem with `addFacet` in a real deployment. If you
reproduce this, or find the actual cause, please update this note.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- To add a *label* with a fixed value instead of a facet, use `relabel`'s `replace` action with an unconditionally-matching `regex` — see `relabel/replace`.
