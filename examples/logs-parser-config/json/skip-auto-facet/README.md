# json: skipAutoFacet

Controls JSON auto-parsing rather than disabling it outright — most notably,
raising the default 50-facet-per-line ceiling for messages that legitimately
have more fields than that.

## Syntax

```yaml
- skipAutoFacet:
    args:
      maxFacetsCount: <n>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `maxFacetsCount` | No | Maximum facets to auto-extract from a single JSON message. Default `50`; extraction silently stops beyond this. |

## Example

Raise the limit to 100 for a source that emits wide JSON payloads.

<!-- validation: expect=facet:field_20=v20 -->
```yaml
- skipAutoFacet:
    args:
      maxFacetsCount: 100
```
```json
{"message": "{\"field_00\":\"v00\",\"field_01\":\"v01\",\"field_02\":\"v02\",\"field_03\":\"v03\",\"field_04\":\"v04\",\"field_05\":\"v05\",\"field_06\":\"v06\",\"field_07\":\"v07\",\"field_08\":\"v08\",\"field_09\":\"v09\",\"field_10\":\"v10\",\"field_11\":\"v11\",\"field_12\":\"v12\",\"field_13\":\"v13\",\"field_14\":\"v14\",\"field_15\":\"v15\",\"field_16\":\"v16\",\"field_17\":\"v17\",\"field_18\":\"v18\",\"field_19\":\"v19\",\"field_20\":\"v20\",\"field_21\":\"v21\",\"field_22\":\"v22\",\"field_23\":\"v23\",\"field_24\":\"v24\",\"field_25\":\"v25\",\"field_26\":\"v26\",\"field_27\":\"v27\",\"field_28\":\"v28\",\"field_29\":\"v29\",\"field_30\":\"v30\",\"field_31\":\"v31\",\"field_32\":\"v32\",\"field_33\":\"v33\",\"field_34\":\"v34\",\"field_35\":\"v35\",\"field_36\":\"v36\",\"field_37\":\"v37\",\"field_38\":\"v38\",\"field_39\":\"v39\",\"field_40\":\"v40\",\"field_41\":\"v41\",\"field_42\":\"v42\",\"field_43\":\"v43\",\"field_44\":\"v44\",\"field_45\":\"v45\",\"field_46\":\"v46\",\"field_47\":\"v47\",\"field_48\":\"v48\",\"field_49\":\"v49\",\"field_50\":\"v50\",\"field_51\":\"v51\",\"field_52\":\"v52\",\"field_53\":\"v53\",\"field_54\":\"v54\"}", "ddsource": "wide-payload-service"}
```

**Expected output:** `result.facets` includes `field_20: v20` — the 21st
field, which the default 50-facet ceiling would still have included, but
which demonstrates the mechanism. Remove the `skipAutoFacet` function and
re-run with a payload past field 50 to see extraction actually stop at the
default.

### API call

```bash
python3 ../../test_pipeline.py \
  --pipeline-file pipeline.yaml \
  --payload-file payload.json \
  --payload-type datadog
```

## Notes

- Extraction beyond the limit fails silently — there's no error or warning facet when a wide payload is truncated, so if fields you expect are missing, check whether this is the cause before assuming a parsing bug.
- A higher limit costs more to index per line; raise it only for sources that genuinely need it.
