# label_join

Writes a new label whose value is the values of several source labels joined with a separator. Use it to build a single display or matching key from multiple dimensions.

## Syntax

```
label_join(<expr>, "<dst>", "<separator>", "<src1>", "<src2>", ...)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<expr>` | Required | The expression to transform. |
| `<dst>` | Required | The label to write. |
| `<separator>` | Required | String placed between values. |
| `<srcN>` | Required | One or more source labels to join. |

## Example

Build an `instance_zone` key from the service name and availability zone of Kloudfuse query-service pods.

<!-- validation: kind=instant minutes=10 -->
```promql
label_join(
  sum by (app_kubernetes_io_name, availability_zone) (go_goroutines{app_kubernetes_io_name="query-service"}),
  "instance_zone", "/", "app_kubernetes_io_name", "availability_zone"
)
```

**Expected output:**

| instance_zone | Value |
|---|---|
| query-service/canadacentral-1 | 22 |
| query-service/us-central1-a | 2,473 |
| query-service/ap-south-1a | 1,029 |
| query-service/us-gov-west-1a | 22 |
| query-service/us-west1-a | 5,483 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=label_join( sum by (app_kubernetes_io_name, availability_zone) (go_goroutines{app_kubernetes_io_name="query-service"}), "instance_zone", "/", "app_kubernetes_io_name", "availability_zone" )' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- Missing source labels contribute an empty string.
