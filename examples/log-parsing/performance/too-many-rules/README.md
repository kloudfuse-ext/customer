# Performance: too many configured rules slow the pipeline down

Demonstrates the troubleshooting guide's "too many configured rules will slow
down the pipeline" scenario. Unlike the other recipes in this repo, this one
is **not** validated through the Pipeline API's `/pipeline/test-function`
endpoint — it's validated through the same PromQL metrics the troubleshooting
guide tells you to watch, against a real deployed `logs-parser`, because the
effect being demonstrated (sustained CPU cost, real Kafka consumer
throughput) only shows up under an actual running pipeline, not a single
synthetic request.

**This changes a live deployment's config and measurably raises its CPU
usage. Only run this against a disposable or lower environment you can roll
back — never production.**

## Use case

A platform team has been onboarding new tenants onto a shared Kloudfuse
deployment for over a year. Every onboarding runbook includes a step to add a
`relabel` rule tagging that tenant's logs with a `tenant_id` label, so the
rule count has grown by one with every new tenant — unnoticed, past 2,000.
Someone eventually notices `logs-parser` running hotter than it used to and
starts investigating, assuming the cause is rising log volume rather than the
accumulated rule count.

## The scenario

Every `relabel`/`transform` function pays its `conditions`-evaluation cost on
every log line that reaches it, whether or not it matches. A config that
accumulates thousands of rules over time — even mostly-dormant ones scoped to
sources that rarely appear — adds real per-event overhead that scales with
rule *count*, not match rate.

## Reproduce it

```bash
# 1. Generate an overlay of 2,000 no-op relabel rules (none of them ever
#    match — each is scoped to a source that will never appear).
python3 generate_stress_config.py --rules 2000 --out stress.yaml

# 2. Deploy it on top of your existing values, in a lower environment.
helm upgrade kfuse <chart> -n <namespace> --reuse-values -f stress.yaml

# 3. Watch logs-parser CPU via PromQL (your deployment's own Metrics
#    Explorer / API) — see troubleshooting.adoc's "Too many configured rules"
#    section for the full query set:
#      max(container_cpu_usage{kube_namespace="<namespace>", kube_container_name="logs-parser"})

# 4. Roll back when done.
helm rollback kfuse <previous-revision> -n <namespace>
```

## Confirmed result

Deploying the 2,000-rule overlay to a running `logs-parser`, with zero change
in log volume, raised steady-state CPU roughly **28x** over its pre-change
baseline (observed via `container_cpu_usage` on the deployment's own
platform). CPU returned to baseline within a few minutes of rolling the
config back.

The cost comes entirely from evaluating `conditions` — every generated rule
is scoped to a source that never appears, so none of them ever actually fire
or change a single log's output.

## What to do about it

See the troubleshooting guide's "What to do about it" for this section —
consolidating `conditions`, removing rules for retired sources, and
periodically auditing rule count the way you'd audit metric or label
cardinality.

## Generic pattern

This is the shape of rule that tends to accumulate one-per-tenant until it's
a performance problem; the fix is consolidating many of these into fewer,
more general rules, not any single rule's logic:

```yaml
- relabel:
    args:
      - action: "replace"
      - regex: ".*"
      - replacement: "<tenant-id>"
      - targetLabel: "tenant_id"
    conditions:
      - matcher: "#source"
        value: "<tenant-source>"
        op: "=="
```
