# relabel: drop

Discards the log line entirely if the joined `sourceLabels` value matches
`regex`. Use it to filter out noisy, low-value lines (health checks, readiness
probes) before they're indexed at all.

## Syntax

```yaml
- relabel:
    args:
      - action: "drop"
      - sourceLabels: "<label-or-facet-list>"
      - separator: "<separator>"    # optional; default ""
      - regex: "<regex>"
    conditions:                     # optional
      - matcher: <label|facet|field>
        value: "<expected-value>"
        op: "<op>"
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `sourceLabels` | Yes | Comma-separated labels/facets to read and join with `separator` before matching. |
| `separator` | No | String used to join multiple `sourceLabels` values. |
| `regex` | Yes | Pattern that, if matched, drops the line. |

## Example

Drop health-check lines once a `path` facet (extracted from the JSON message
body) equals `/healthz`.

<!-- validation: expect=manual -->
```yaml
- relabel:
    args:
      - action: "drop"
      - sourceLabels: "@path"
      - regex: "/healthz"
```
```json
{"message": "{\"path\": \"/healthz\", \"status\": 200}", "ddsource": "checkout-api"}
```

**Expected effect (in a real deployment):** the line is discarded — it will
not appear in the Logs Explorer once this rule is deployed. A dropped line
through this test API comes back as `{"success": false, "error": "Event was
dropped by the pipeline"}` (verified directly against a live `logs-parser`).

**Verified limitation of this test tool:** `POST /pipeline/test-function`
inserts your snippet *before* the pipeline's built-in JSON auto-parsing
stage, so `@path` is empty at the point this `drop` condition evaluates here
— the line will *not* actually be dropped when you run this example, even
though the YAML is correct for a real deployment where you control the
function's position in the full `config` list directly. This example is
marked `expect=manual` because it cannot be automatically verified through
this endpoint; confirm facet-dependent `drop` behavior by deploying to a
lower environment instead.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- `sourceLabels` is required for `drop`/`keep` — without it, the joined value is always empty and the regex is matched against `""`.
- To drop only lines matching *and* from a specific source, add a `conditions` block scoping the function to `#source`.
