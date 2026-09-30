# json: automatic facet extraction

No configuration needed — this is the default behavior for any log whose
message is valid JSON. Every property becomes a facet automatically, with
nested objects flattened using `_` and arrays extracted as a single string
facet. This example exists to show the behavior you get for free, before you
reach for a custom `parser` pattern.

## Syntax

Nothing to configure — this runs whenever a message parses as JSON, with no
pipeline function required.

## Example

A nested JSON message, parsed with no pipeline configuration at all.

<!-- validation: expect=facet:location_city=SF -->
```yaml
# no pipeline function needed — JSON auto-parsing is a built-in default
```
```json
{"message": "{\"user\": \"johndoe\", \"location\": {\"city\": \"SF\"}, \"aliases\": [\"johndoe\", \"johnny\"]}", "ddsource": "profile-service"}
```

**Expected output:** `result.facets` includes `user: johndoe`,
`location_city: SF` (the nested `location.city` flattened), and
`aliases: johndoe,johnny` (the array extracted as a single string facet).

### API call

```bash
python3 ../../test_pipeline.py \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- No `--pipeline-file` above — this calls `POST /pipeline/test` directly against the currently loaded pipeline, whose built-in defaults already include JSON auto-parsing. Nothing needs to be added to `kf_parsing_config` for this behavior.
- A single log line produces at most 50 facets by default; see `json/skip-auto-facet` for raising that limit.
- Once ingested, query these facets from the Logs Explorer the same way as any manually extracted one — no distinction is made in search.
