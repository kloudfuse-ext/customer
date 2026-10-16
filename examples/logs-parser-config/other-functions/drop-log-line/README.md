# dropLogLine

Unconditionally drops the log line. On its own it would drop every line the
pipeline processes, so it's used almost exclusively with a `conditions`
block — the pipeline's way to exclude a whole category of logs at ingest,
rather than filtering them out of every query afterward.

## Syntax

```yaml
- dropLogLine:
    conditions:
      - matcher: <label|facet|field>
        value: "<expected-value>"
        op: "<op>"
```

## Parameters

`dropLogLine` takes no `args` — everything is in `conditions`.

## Example

Drop debug-level logs from a specific noisy source entirely, rather than
filtering them out at query time.

<!-- validation: expect=dropped -->
```yaml
- dropLogLine:
    conditions:
      - matcher: "%kf_msg"
        value: "DEBUG"
        op: "contains"
      - matcher: "#source"
        value: "chatty-sidecar"
        op: "=="
```
```json
{"message": "DEBUG heartbeat tick", "ddsource": "chatty-sidecar"}
```

**Expected output:** `{"success": false, "error": "Event was dropped by the
pipeline"}` — verified directly against a live `logs-parser`. The line is
discarded before indexing; it will not appear in the Logs Explorer once this
rule is deployed. Unlike the facet-based `relabel: drop`/`keep` examples,
this one's `conditions` match on the raw message (`%kf_msg`) and a label
(`#source`) rather than an auto-extracted facet, so it isn't affected by the
test endpoint's facet-timing limitation — swap the payload's `ddsource` to
something other than `chatty-sidecar` to see the non-dropped case return
normally.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- Multiple `conditions` entries are ANDed together — this example only drops lines that are both from `chatty-sidecar` *and* contain `DEBUG`.
- `relabel`'s `drop` action (see `relabel/drop`) achieves the same outcome by matching a facet/label value instead of the raw message; use whichever condition style fits the check you need.
