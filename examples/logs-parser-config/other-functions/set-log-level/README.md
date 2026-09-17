# setLogLevel

Forces a log's level to a fixed value, overriding whatever automatic
detection produced. Use it for sources whose level isn't detectable from the
message at all (a source that's always informational, or always an error
once it reaches this pipeline).

## Syntax

```yaml
- setLogLevel:
    args:
      - level: "<level>"
    conditions:    # optional — almost always needed, to scope to the right source
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `level` | Yes | The level to set, unconditionally overriding automatic detection. |

## Example

A heartbeat source with no level information in its message — force every
line from it to `INFO`.

<!-- validation: expect=level:info -->
```yaml
- setLogLevel:
    args:
      - level: "INFO"
    conditions:
      - matcher: "#source"
        value: "heartbeat"
        op: "=="
```
```json
{"message": "tick", "ddsource": "heartbeat"}
```

**Expected output:** `result.logLevel` is `info` — verified against a live
`logs-parser`: the API lower-cases `logLevel` in its response regardless of
the case you set in `args.level`.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- Without `conditions`, this overrides the level for *every* log the pipeline processes — almost always scope it to a specific source.
