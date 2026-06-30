# cosh

Returns the hyperbolic cosine of a number. Defined as `(e^x + e^(-x)) / 2`. Always returns a value ≥ 1.

## Syntax

```fuseql
| cosh(<number>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<number>` | Required | A numeric field name or literal value. |
| `as <alias>` | Required | Output column name for the result. |

## Example

Compute `cosh(0)` = 1.0.

```fuseql
source="nginx"
| timeslice 1h
| count as requests by _timeslice
| cosh(0) as cosh_0
```

**Expected output:**

| _timeslice | cosh_0 |
|---|---|
| 2026-06-27 18:00:00 UTC | 1.0 |
| 2026-06-27 19:00:00 UTC | 1.0 |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | timeslice 1h | count as requests by _timeslice | cosh(0) as cosh_0\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders TableResult } }"}'
```

## Notes

- `cosh(0)` = 1.0. Unlike `cos`, `cosh` is unbounded above: `cosh(10)` ≈ 11,013.
- Do not apply `cosh` directly to large raw field values — results will overflow.
