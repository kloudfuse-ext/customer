# dbscan

Kloudfuse extension. Clusters the input series by shape using DBSCAN and flags series that do not belong to any cluster — the fleet members behaving unlike their peers. See the Kloudfuse docs.

## Syntax

```
dbscan(<expr>, <tolerance>, <norm-constant>, <result-type>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<tolerance>` | Required | Sensitivity, between 0.33 and 5.0 inclusive; lower values are more sensitive to deviations. |
| `<norm-constant>` | Required | Normalization constant; use 1. |
| `<result-type>` | Required | Result selector; use 1. |

## Example

Find Kloudfuse services whose goroutine counts behave unlike the rest of the fleet.

<!-- validation: kind=range_metric minutes=180 -->
```promql
dbscan(sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"}), 2.0, 1, 1)
```

**Expected output:**

| app_kubernetes_io_name | Value |
|---|---|
| analytics-service | 0 |
| archive-writer | 0 |
| az-service | 0 |
| config-mgmt-service | 0 |
| envoy-gateway | 0 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query_range" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=dbscan(sum by (app_kubernetes_io_name) (go_goroutines{app_kubernetes_io_instance="kfuse"}), 2.0, 1, 1)' \
  --data-urlencode "start=$(date -u -v-180M +%s)" \
  --data-urlencode "end=$(date -u +%s)" \
  --data-urlencode "step=60"
```

## Notes

- Advance functions run in the Kloudfuse advanced-functions service, not in the PromQL engine, and fit a model per input series. Expect higher latency than standard functions, and aggregate first so the function receives few series — high-cardinality inputs degrade performance or time out.
