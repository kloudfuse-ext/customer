# Security Demo — Masking Sensitive Data Before Ingest

Tests the collector-side masking rules documented in kf-docs
([`reference/datadog/log-processing.adoc`](https://github.com/kloudfuse/kf-docs/blob/main/platform/modules/ROOT/pages/reference/datadog/log-processing.adoc),
[`reference/otel/logs-processing.adoc`](https://github.com/kloudfuse/kf-docs/blob/main/platform/modules/ROOT/pages/reference/otel/logs-processing.adoc),
[`reference/misc/sensitive-data.adoc`](https://github.com/kloudfuse/kf-docs/blob/main/platform/modules/ROOT/pages/reference/misc/sensitive-data.adoc)).

A pod emits JSON logs containing **public test** card numbers, card security codes,
credentials/tokens, and emails. A log agent masks those values **in the agent**, before
anything leaves the node, and forwards the redacted logs to Kloudfuse. Verification
confirms the placeholders arrive and no raw value does.

> **Safety:** only public, non-live test PANs (Visa/Mastercard/Amex/Discover test
> numbers) are used. Never add real cardholder data to this demo.

## Layout

| Path | What it is |
|------|------------|
| [`demo/sensitive-emitter/`](demo/sensitive-emitter/) | Pod that logs test PANs, CSCs, credentials, emails, and decoys |
| [`demo/dd-agent/`](demo/dd-agent/) | Datadog Agent DaemonSet with `mask_sequences` rules |
| [`demo/otel/`](demo/otel/) | OTel Collector DaemonSet with `transform/mask_sensitive` statements |
| [`demo/verify.sh`](demo/verify.sh) | Queries Kloudfuse and asserts masking worked |
| [`validate/`](validate/) | Offline Go RE2 test of the patterns (no cluster needed) |

## Two layers under test

1. **Redaction at collection** — the agent rewrites card numbers, CSCs, credentials, and
   emails to placeholders (`[CARD REDACTED]`, `[CSC REDACTED]`, `[SECRET REDACTED]`,
   `***@***.***`). The captured key and separator are echoed back so masked JSON stays valid.
2. **Detection of what got through** — the FuseQL `luhn` predicate validates card-number
   checksums in a scheduled search, catching real cards a too-narrow rule let past.

## Quick start

Pick **one** agent (dd-agent or otel), then verify.

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=<kloudfuse-token>
NAMESPACE=<your-namespace>

# 1. emitter
sed "s/<NAMESPACE>/$NAMESPACE/; s/<NODE_LABEL>/<node-label>/" \
  demo/sensitive-emitter/manifest.yaml | kubectl apply -f -

# 2. one agent (see the agent README for the helm command and placeholders)

# 3. verify (dd-agent selector shown; pass '{service_name="security-demo"}' for otel)
MINUTES=15 demo/verify.sh
```

## Offline validation (no cluster)

The masking patterns compile with Go RE2 — the exact engine the Datadog Agent and the
OTel Collector use. The Go test applies the identical patterns and `$1$2` replacements to
realistic log lines:

```bash
cd validate && go test -v ./...
```

It asserts every card layout is masked, CSC/Track-2/credentials/emails are masked with
their keys preserved, prose such as "the password was reset" is untouched, and a masked
JSON line stays valid JSON.

## Live test results

Both agents were run on the `dev` cluster, collecting the `security-demo` pod and 
forwarding to Kloudfuse. Masking was verified by capturing what each agent emits 
*after* applying the rules (a request sink for the Datadog Agent; the `debug` exporter 
for the OTel Collector):

- `pan`/card numbers → `[CARD REDACTED]`; `cvv`/`cvc2`/`cid`/`service_code` → `[CSC REDACTED]`;
  `password`/`bearer`/`api_key` → `[SECRET REDACTED]`; emails → `***@***.***`.
- The captured key and separator are echoed back, so masked JSON stays valid JSON — this
  confirmed the Datadog `$1$2` and OTel `$$1$$2` back-references work on real agents.
- Decoys (`order_id`, `trace_id`, and the prose "the password was reset") were untouched.

The run also surfaced a **rule-ordering bug** not caught by the first offline test: with the
broad card rule first, a card number embedded in `track2` was fragmented, leaving the Track 2
discretionary data exposed (`"[CSC REDACTED] REDACTED]=2512..."`). The fix — running the
key-anchored rules (CSC, credentials) *before* the card rule — is now the shipped order here
and in kf-docs, and is locked in by `validate/order_test.go`.

## Detection layer (in Kloudfuse)

Save this as a Scheduled Search with a threshold of zero; a non-zero result names a
service whose masking rule needs attention (expected result with masking on: zero):

```
source="security-demo"
| parse regex "(?P<candidate>[0-9](?:[ -]?[0-9]){12,18})"
| where luhn(candidate)
| count by service
```

## Tear down

```bash
kubectl delete pod security-demo -n $NAMESPACE
# plus: helm uninstall for whichever agent you deployed (see its README)
```
