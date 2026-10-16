# relabel: replace

Regex-matches one or more source labels (joined by `separator`) against
`regex`, and if it matches, writes `replacement` to `targetLabel`. This is
`relabel`'s default action, and the most common one — set a fixed label on
every log, or derive one from an existing value.

## Syntax

```yaml
- relabel:
    args:
      - action: "replace"
      - sourceLabels: "<label-or-facet-list>"   # optional; comma-separated, @facet or #label
      - separator: "<separator>"                # optional; default ""
      - regex: "<regex>"
      - replacement: "<replacement>"
      - targetLabel: "<label-or-@facet>"
    conditions:                                  # optional
      - matcher: <label|facet|field>
        value: "<expected-value>"
        op: "<op>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `sourceLabels` | No | Comma-separated labels/facets to read and join with `separator` before matching. Omit to match against an empty string (useful for an unconditional `replace`). |
| `separator` | No | String used to join multiple `sourceLabels` values. |
| `regex` | Yes | Pattern matched against the joined source value. |
| `replacement` | Yes | Value written to `targetLabel` when `regex` matches. |
| `targetLabel` | Yes | The label to write. Prefix with `@` to write a facet instead. |

## Example

Tag every log from this pipeline with a fixed `env=production` label,
regardless of source.

<!-- validation: expect=tag:env=production -->
```yaml
- relabel:
    args:
      - action: "replace"
      - regex: ".*"
      - replacement: "production"
      - targetLabel: "env"
```
```json
{"message": "GET /health 200 12ms", "ddsource": "checkout-api"}
```

**Expected output:** `result.tags` includes `"env": "production"`.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- To derive a label from an existing one instead of setting a fixed value, set `sourceLabels` and use capture groups in `regex`/`replacement` (standard regex replacement syntax).
- This is logs-only. Metrics, Events, and Traces relabeling is a separate, ingester-level mechanism — see the Relabel Rules docs (Data Management → Routing).
