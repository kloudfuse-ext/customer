# logFmt

Parses the message as [logfmt](https://brandur.org/logfmt) — space-separated
`key=value` pairs — extracting each as a facet. Use it for sources that emit
logfmt instead of JSON or a fixed plain-text shape, without writing a dissect
or grok pattern by hand.

## Syntax

```yaml
- logFmt:
    conditions:    # optional, recommended
```

## Parameters

`logFmt` takes no `args` — it always parses the whole message as logfmt when
it runs.

## Example

Extract fields from a logfmt-style application log line.

<!-- validation: expect=facet:method=Authorise -->
```yaml
- logFmt:
    conditions:
      - matcher: "#source"
        value: "auth-service"
        op: "=="
```
```json
{"message": "ts=2026-07-04T15:37:52Z caller=logging.go:29 method=Authorise result=false took=9.775ms", "ddsource": "auth-service"}
```

**Expected output:** `result.facets` includes `ts: 2026-07-04T15:37:52Z`,
`caller: logging.go:29`, `method: Authorise`, `result: false`, and
`took: 9.775ms`.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- Scope with `conditions` — an unscoped `logFmt` runs against every source, and misparses messages that aren't actually logfmt.
- Kloudfuse's automatic heuristic already attempts logfmt-style extraction for plain-text messages; add this explicitly when the heuristic isn't reliable enough for a specific source.
