# unpack

Unpacks log lines that an agent packed with Promtail's `pack` stage, which wraps the original line in a JSON envelope together with extra labels. `unpack` restores the embedded labels and replaces the line with the original `_entry` content. Lines that were not packed pass through unchanged.

## Syntax

```
| unpack
```

## Example

Apply `unpack` to a stream. Filebeat lines are not packed, so they flow through unmodified — demonstrating that `unpack` is safe to apply even when only part of the stream is packed.

<!-- validation: kind=range minutes=30 -->
```logql
{source="filebeat"} | unpack
```

**Expected output:**

```
{"log.level":"info","@timestamp":"2026-07-04T15:41:22.410Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:40:52.410Z","log.logger":"monitoring","log.origin":{"file.name ...
{"log.level":"info","@timestamp":"2026-07-04T15:40:22.411Z","log.logger":"monitoring","log.origin":{"file.name ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="filebeat"} | unpack' \
  --data-urlencode "start=$(date -u -v-30M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- `unpack` only restores envelopes with the `_entry` property produced by the pack stage; it is not a general JSON parser — use `json` for that.
