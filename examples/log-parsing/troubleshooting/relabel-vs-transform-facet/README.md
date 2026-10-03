# Troubleshooting: a facet_to_label_map promotion silently does nothing as relabel

Demonstrates the troubleshooting guide's "a promoted facet does not show up as
a label" case, and the best-practices "Relabel, Transform priority order"
rule. `relabel` and `transform` run the identical action engine, but `relabel`
always executes in a fixed stage *before* Grammar — so a `relabel` rule can
never see a facet `grok`/`dissect` just extracted, no matter where you place
it in the `config` list. `transform` always executes after. This is not
locally simulable (it depends on pipeline stage ordering, not the action
logic alone), so this recipe is verified against a running cluster rather
than a local tester — see `../../dissect_tester.py` etc. for the ones that
are.

## Use case

A team instruments a payments service that logs plain-text request lines,
extracts the caller's IP as a facet with `grok` so it's visible per-line, and
wants to promote it to a label so dashboards can filter and group by client
IP without digging into individual lines. They reach for `relabel` — the
first action-capable function they find in the configuration reference —
without realizing it runs in an earlier pipeline stage than Grammar.

## Sample line

```
checkout request from 10.1.2.3
```

## The broken config

Extracts `client_ip` with `grok`, then tries to promote it to a `client`
label with `relabel`:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - parser:
          grok:
            args:
              - patterns:
                  - '%{WORD:service} request from %{IP:client_ip}'
      - relabel:
          args:
            - action: "facet_to_label_map"
            - sourceLabels: "@client_ip"
            - targetLabel: "client"
```

## Broken result

`client_ip` is extracted correctly as a facet, but no `client` label is ever
created — confirmed against a running `logs-parser` via `/pipeline/test-function`:

```json
{
  "facets": {"service": "checkout", "client_ip": "10.1.2.3"},
  "tags": {"agent": "datadog", "source": "unknown"}
}
```

No error, no warning — `relabel` ran in its own stage before `grok` ever
extracted `client_ip`, so from `relabel`'s point of view the facet simply
didn't exist yet.

## The fix

Change `relabel` to `transform` — nothing else changes:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - parser:
          grok:
            args:
              - patterns:
                  - '%{WORD:service} request from %{IP:client_ip}'
      - transform:
          args:
            - action: "facet_to_label_map"
            - sourceLabels: "@client_ip"
            - targetLabel: "client"
```

## Fixed result

```json
{
  "facets": {"service": "checkout", "client_ip": "10.1.2.3"},
  "tags": {"agent": "datadog", "client": "10.1.2.3", "source": "unknown"}
}
```

## Generic pattern

Promoting any Grammar-extracted facet to a label always takes this shape,
with `transform` after the extraction step, never `relabel`:

```yaml
- parser:
    grok:    # or dissect, or rely on JSON auto-parsing
      args:
        - patterns:
            - '<pattern extracting @facet-name>'
- transform:
    args:
      - action: "facet_to_label_map"
      - sourceLabels: "@<facet-name>"
      - targetLabel: "<label-name>"
```

See xref (in the Kloudfuse docs) `data-management/log-parsing/best-practices.adoc#order-deliberately`.
