# sinh

Returns the hyperbolic sine of a number. Defined as `(e^x − e^(-x)) / 2`. Can return any real number and grows rapidly for large inputs.

## Syntax

```fuseql
| sinh(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute `sinh(0)` = 0.0.

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| sinh(0) as sinh_0
```

**Expected output:**

| _timeslice | sinh_0 |
|---|---|
| 2026-06-27 18:00:00 UTC | 0.0 |
| 2026-06-27 19:00:00 UTC | 0.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | sinh(0) as sinh_0\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `sinh(0)` = 0.0. `sinh(1)` ≈ 1.1752.
- Unlike `sin`, `sinh` is unbounded. Do not apply it directly to large raw field values — normalize first.
