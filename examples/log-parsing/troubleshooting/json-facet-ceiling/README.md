# Troubleshooting: a wide JSON payload has no facets at all

Demonstrates the troubleshooting guide's "a wide JSON payload has no facets
at all" case. JSON auto-parsing extracts at most 50 facets from a single log
line by default — but this is an all-or-nothing ceiling, not a truncation.
Crossing it doesn't lose the facets past 50; it loses *all* of them. This is
tracked as a product issue: kloudfuse/bugzilla#1701.

Not locally simulable (JSON auto-parsing isn't `dissect`/`grok`), so this is
verified directly against a running cluster.

## Use case

A billing-events service emits JSON events that can carry a lot of optional
metadata — line items, discounts, customer attributes. Ordinary events have a
dozen or so fields, but a fully-populated enterprise-plan event can carry 60
or more. The team expects Kloudfuse to facet all of it the way it does for
their other, narrower JSON sources, and only notices something's wrong when
this specific source turns out to have zero searchable facets in the
Explorer, even though ingestion volume looks completely normal.

## The scenario

A JSON log line with 50 string fields, and the same line with one more field
added (51 total) — nothing else different.

## Results, confirmed against a running `logs-parser` via `/pipeline/test-function`

| Fields in the JSON object | Facets extracted |
|---|---|
| 50 | 50 |
| 51 | **0** |

No error, no warning, no partial facet set — the 51-field line produces an
empty `facets` map.

## Fix 1: raise the ceiling

If the source is legitimately this wide:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - skipAutoFacet:
          args:
            maxFacetsCount: 100
```

Confirmed: the same 51-field line now produces all 51 facets.

## Fix 2: narrow to what you need instead

If most of those fields aren't actually useful to search or filter on,
extract only the ones you name — this keeps the line safely under the
ceiling regardless of how many fields the source sends:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - whitelistFacets:
          args:
            facets:
              - "f0"
```

Confirmed: the same 51-field line now produces exactly the one named facet
(`f0`), untouched by the ceiling.

## Generic pattern

Either template applies as-is to any JSON source that occasionally exceeds
the default ceiling; pick based on whether you need every field or only a
known few:

```yaml
- skipAutoFacet:
    args:
      maxFacetsCount: <new-ceiling>
```

```yaml
- whitelistFacets:
    args:
      facets:
        - "<facet-you-actually-need>"
        - "<another-facet-you-need>"
```
