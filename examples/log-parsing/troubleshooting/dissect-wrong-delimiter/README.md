# Troubleshooting: wrong delimiter produces wrong facets, not an error

Demonstrates the troubleshooting guide's "if a field's value contains more
text than expected, check the literal delimiter" case. A `dissect` tokenizer
built for one delimiter character silently produces wrong facets — not an
error — against a line that uses a different one.

## Use case

A team onboards a legacy internal proxy that logs pipe-delimited `key:value`
pairs instead of JSON, and wants `user`, `action`, and `status` as separate
facets so they can filter failed logins by user in the Explorer. They adapt a
tokenizer copied from another team's comma-delimited source, updating the
field names but not the delimiter character.

## The broken config

The line uses `|` to separate fields, but the tokenizer was written for `,`:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - parser:
          dissect:
            args:
              - tokenizer: '%{user}:%{uval},%{action}:%{aval},%{status}:%{sval}'
```

## Sample line

```
user:alice|action:login|status:success
```

## Broken result

Only two facets come out, and `uval` has absorbed everything after the first
colon instead of just `alice`:

```json
{"uval": "alice|action:login|status:success", "user": "user"}
```

The pattern doesn't fail — it matches as far as it can (up to the first
literal `:` it finds) and then has nowhere to go once the `,` it's looking
for never appears, silently discarding the rest of the pattern rather than
erroring.

## The fix

Match the actual delimiter:

```yaml
logs-parser:
  kf_parsing_config:
    config: |-
      - parser:
          dissect:
            args:
              - tokenizer: '%{user}:%{uval}|%{action}:%{aval}|%{status}:%{sval}'
```

## Fixed result

```json
{"user": "user", "uval": "alice", "action": "action", "aval": "login", "status": "status", "sval": "success"}
```

## Generic pattern

Any line structured as repeated `key:value` pairs joined by one consistent
delimiter follows this shape; substitute your own field names and delimiter
character:

```yaml
- parser:
    dissect:
      args:
        - tokenizer: '%{field1}:%{value1}<delimiter>%{field2}:%{value2}<delimiter>%{field3}:%{value3}'
```

## Validation

<!-- validation: kind=dissect -->
```json
{
  "tokenizer": "%{user}:%{uval}|%{action}:%{aval}|%{status}:%{sval}",
  "line": "user:alice|action:login|status:success",
  "expected": {
    "user": "user",
    "uval": "alice",
    "action": "action",
    "aval": "login",
    "status": "status",
    "sval": "success"
  }
}
```

Confirmed against a running `logs-parser` via `/pipeline/test-function` — both
the broken and fixed results above are real API responses, not simulated.
