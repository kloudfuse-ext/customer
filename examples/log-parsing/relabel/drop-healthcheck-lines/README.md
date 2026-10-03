# Transform: drop noisy health-check lines

Discards the log line entirely when a facet matches, instead of writing a
label or facet. Uses `transform`, not `relabel` — see the note below.

## Pipeline config

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - transform:
          args:
            - action: "drop"
            - sourceLabels: "@path"
            - regex: "/healthz"
```

## Why `transform`, not `relabel`

Confirmed against a running logs-parser's `/pipeline/test-function` API:
`relabel` and `transform` run the same action engine, but they are not
interchangeable by position the way the docs' "transform is just relabel
placed later by convention" framing suggests. `relabel` always executes in a
fixed early stage — before Grammar, JSON auto-parsing, or any other facet
extraction runs — regardless of where you place it in the `config` list.
A `relabel` rule can only see labels/facets the agent envelope already
carried in, never a facet your own pipeline config extracts. `transform`
always executes after extraction. If a `drop`/`keep`/`replace` condition
depends on a facet from `dissect`, `grok`, `addFacet`, or JSON auto-parsing,
it must be written as `transform`; writing it as `relabel` silently never
matches, because the facet doesn't exist yet when `relabel` runs.

## Before / after

Given the facet `path: /healthz` (already extracted by an earlier Grammar
step), the log line is dropped — it never reaches the Logs Store, so there is
no "after" facet/label state to inspect.

## Validation

<!-- validation: kind=relabel -->
```json
{
  "args": {"action": "drop", "sourceLabels": "@path", "regex": "/healthz"},
  "input": {"facets": {"path": "/healthz"}, "labels": {}},
  "expected": {"dropped": true}
}
```
