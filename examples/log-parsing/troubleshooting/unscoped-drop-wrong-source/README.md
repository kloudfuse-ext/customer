# Troubleshooting: an unscoped drop condition catches lines it wasn't meant for

Demonstrates best-practices' "Scope every function with conditions" rule. A
condition that matches on message text alone, with no source scoping, applies
pipeline-wide — not just to the noisy source you had in mind. Verified against
a running cluster rather than a local tester, since this depends on
cross-payload condition matching, not a single action's logic.

## Use case

An SRE team wants to cut ingestion noise from a chatty nginx sidecar's
`/healthz` liveness probe, which fires every few seconds with no diagnostic
value. They write a `dropLogLine` rule matching the literal text, intending
it only for that one source — but since they were only looking at nginx's
logs while writing it, they never add a source scope, and the rule applies to
every source in the pipeline.

## Sample lines

An nginx health-check line you actually want dropped:

```
GET /healthz from payments-service healthz-checker
```

An unrelated line from a different source that happens to mention "healthz":

```
incident report: customer mentioned healthz endpoint flakiness in ticket #4821
```

## The broken config

Drops any line whose message contains "healthz" — no `#source` scoping:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - dropLogLine:
          conditions:
            - matcher: "%kf_msg"
              value: "healthz"
              op: "contains"
```

## Broken result

Confirmed against a running `logs-parser` via `/pipeline/test-function`: **both**
lines are dropped, including the unrelated incident report that merely
mentions the word.

```json
{"success": false, "error": "Event was dropped by the pipeline"}
```

(Same response for both sample lines above.)

## The fix

Add a `#source` matcher so the condition only applies to the source it was
written for:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - dropLogLine:
          conditions:
            - matcher: "#source"
              value: "nginx"
              op: "=="
            - matcher: "%kf_msg"
              value: "healthz"
              op: "contains"
```

## Fixed result

Confirmed against a running `logs-parser`: the nginx line is still dropped,
but the unrelated line (source `support-bot`) now passes through untouched:

```json
{"success": true, "result": {"originalMessage": "incident report: customer mentioned healthz endpoint flakiness in ticket #4821", "tags": {"source": "support-bot"}, "facets": {"report": "customer"}}}
```

## Generic pattern

Any condition meant to apply to one source needs an explicit `#source`
matcher alongside the condition that expresses the actual intent; never rely
on the content match alone to imply the scope:

```yaml
- dropLogLine:        # or keep, or any other conditions-scoped function
    conditions:
      - matcher: "#source"
        value: "<source-to-scope-to>"
        op: "=="
      - matcher: "%kf_msg"    # or a facet/label matcher
        value: "<text-to-match>"
        op: "contains"
```
