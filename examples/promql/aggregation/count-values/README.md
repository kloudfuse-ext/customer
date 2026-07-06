# count_values

Groups the input series by their sample value and counts how many series hold each value, writing the value itself into a new label. Use it for discrete-valued metrics — versions, capacities, states — to see the distribution at a glance.

## Syntax

```
count_values("<label>", <expr>)
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<label>` | Required | The label that will carry each distinct value. |

## Example

Count how many node-capacity series report each distinct CPU capacity value.

<!-- validation: kind=instant minutes=10 -->
```promql
count_values("cores", kubernetes_state_node_cpu_capacity)
```

**Expected output:**

| cores | Value |
|---|---|
| 96 | 31 |
| 10000 | 1 |
| 48 | 8 |
| 1 | 4 |
| 16 | 159 |

### API Call

```bash
curl -s -G "https://<kloudfuse-hostname>/api/v1/query" \
  -H "Authorization: Bearer <token>" \
  --data-urlencode 'query=count_values("cores", kubernetes_state_node_cpu_capacity)' \
  --data-urlencode "time=$(date -u +%s)"
```

## Notes

- High-cardinality float metrics explode into one group per distinct value — reserve `count_values` for discrete values.
