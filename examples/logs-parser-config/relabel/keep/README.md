# relabel: keep

The inverse of `drop` — discards the log line unless the joined
`sourceLabels` value matches `regex`. Use it to build an allowlist instead of
a denylist: only lines matching the pattern survive.

## Syntax

```yaml
- relabel:
    args:
      - action: "keep"
      - sourceLabels: "<label-or-facet-list>"
      - separator: "<separator>"    # optional; default ""
      - regex: "<regex>"
    conditions:                     # optional
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `sourceLabels` | Yes | Comma-separated labels/facets to read and join with `separator` before matching. |
| `separator` | No | String used to join multiple `sourceLabels` values. |
| `regex` | Yes | Pattern that must match, or the line is dropped. |

## Example

Keep only lines whose JSON `level` field (auto-extracted as the `level`
facet) is `ERROR` — everything else from this source is discarded.

<!-- validation: expect=manual -->
```yaml
- relabel:
    args:
      - action: "keep"
      - sourceLabels: "@level"
      - regex: "ERROR"
```
```json
{"message": "{\"level\": \"ERROR\", \"msg\": \"payment declined\"}", "ddsource": "checkout-api"}
```

**Expected effect (in a real deployment):** this line's `level` facet is
`ERROR`, so it passes the filter and its facets show up normally; a line
whose `level` is anything else is dropped.

**Verified limitation of this test tool:** `POST /pipeline/test-function`
inserts your snippet *before* the pipeline's built-in JSON auto-parsing
stage — confirmed by testing directly against a live `logs-parser` — so a
`keep`/`drop` condition that reads an auto-extracted facet (`@level`,
`@path`, and so on) sees an empty value here regardless of where in your own
snippet you place it, and behaves as if nothing matched. This is a property
of the test endpoint's merge order, not of `relabel` itself — the YAML above
is correct for a real deployment, where you control the function's position
in the full `config` list directly. This example is marked `expect=manual`
because it cannot be automatically verified through this endpoint; confirm
facet-dependent `keep`/`drop` behavior by deploying to a lower environment
instead.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- `keep` and `drop` are complements: `keep` with `regex: "ERROR"` behaves like `drop` with a regex matching everything *except* `ERROR`.
