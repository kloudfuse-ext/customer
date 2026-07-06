# unwrap

Selects a label whose value becomes the metric sample for the surrounding range aggregation, instead of counting lines. `unwrap` is the bridge between parsed log fields and statistics: extract a latency, size, or count with a parser, unwrap it, and aggregate it with any `*_over_time` function. Values that are not plain numbers need a conversion function: `duration(label)` parses Go durations such as `28.8ms`, and `bytes(label)` parses sizes such as `2KB`.

## Syntax

```
<agg>_over_time({<selector>} <pipeline> | unwrap <label> [<range>]) [by (<labels>)]
| unwrap duration(<label>)   # convert 28.8ms-style values
| unwrap bytes(<label>)      # convert 2KB-style values
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The label to use as the sample value. Must parse as a number after optional conversion. |
| `duration(<label>)` | Optional | Parses the label as a Go duration and yields seconds. |
| `bytes(<label>)` | Optional | Parses the label as a byte size and yields bytes. |

## Example

Extract each nginx request's upstream response time with a regexp, unwrap it, and average it over one-minute windows. The `by (source)` grouping collapses the result to a single series.

<!-- validation: kind=instant minutes=3 -->
```logql
avg_over_time(
  {source="nginx"}
  | regexp "(?P<req_time>[0-9]+[.][0-9]+) [[]"
  | unwrap req_time [1m]
) by (source)
```

**Expected output:**

| source | Value |
|---|---|
| nginx | 0.166 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=avg_over_time( {source="nginx"} | regexp "(?P<req_time>[0-9]+[.][0-9]+) [[]" | unwrap req_time [1m] ) by (source)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Lines whose label fails to parse are dropped from the aggregation and flagged with `__error__`.
- `duration_seconds()` is an alias of `duration()`.
