# Security Demo — Offline Pattern Validation

Validates the masking patterns **without a cluster**. The Datadog Agent
(`mask_sequences`) and the OTel Collector (`transform` `replace_pattern`) both compile
these patterns with Go's `regexp` package (RE2) and substitute with `$1`/`$2` group
references. This test applies the identical patterns and replacements, so a pass here
means the rules behave the same way in either agent.

## Run

```bash
go test -v ./...
```

## What it checks

- **Redaction** — Visa/Mastercard/Amex/Discover test PANs (contiguous, spaced, dashed,
  15-digit), CVV/CVC/CID, Track 2 with its leading `;` sentinel, `password`/`bearer`/
  `api_key` tokens, and emails are all replaced with their placeholders.
- **No false positives** — prose such as "the password was reset", "enter your cvv",
  short numbers, and phone numbers are left unchanged.
- **JSON validity** — a masked JSON log line still parses as JSON, because the CSC and
  credential rules echo the captured key + separator (`$1$2`) and replace only the value.
- **Documented over-match** — a card-prefixed identifier (e.g. an order number beginning
  `4000…`) is masked, locking in the behavior the docs call out so a future pattern change
  that silently stops over-matching is caught.

Keep the patterns in `mask_test.go` in sync with the YAML in `../demo/dd-agent/` and
`../demo/otel/` and with the kf-docs source pages.
