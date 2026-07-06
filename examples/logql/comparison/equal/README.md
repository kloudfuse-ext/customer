# Equal (=)

Selects log streams whose label value is exactly equal to the given string. This is the most common matcher and the fastest, because it resolves directly against the label index. Every LogQL query needs at least one non-empty matcher in its stream selector.

## Syntax

```
{<label>="<value>"}
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | An indexed stream label, such as `source`, `level`, `host`, or `kube_namespace`. |
| `<value>` | Required | The exact string to match. Comparison is case-sensitive. |

## Example

Select all log lines from the `nginx` ingress controller. Each returned line is a raw nginx access-log entry.

<!-- validation: kind=range minutes=10 -->
```logql
{source="nginx"}
```

**Expected output:**

```
10.150.4.1 - - [04/Jul/2026:15:38:04 +0000] "POST /v1/input HTTP/2.0" 200 0 "-" "datadog-agent/7.79.1" 3920 0.013 [kfuse ...
10.150.4.1 - - [04/Jul/2026:15:38:04 +0000] "POST /ingester/intake/ HTTP/2.0" 200 0 "-" "datadog-agent/7.79.1" 12476 0.0 ...
10.20.0.44 - - [04/Jul/2026:15:38:04 +0000] "POST /v1/input HTTP/2.0" 200 0 "-" "datadog-agent/7.79.1" 26081 0.026 [kfus ...
```

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/loki/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query={source="nginx"}' \
  --data-urlencode "start=$(date -u -v-10M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "limit=10"
```

## Notes

- Combine multiple matchers by separating them with commas: `{source="nginx", level="error"}`. All matchers must hold at the same time.
- More selective stream selectors scan less data. Prefer adding a label matcher over filtering the same value later in the pipeline.
