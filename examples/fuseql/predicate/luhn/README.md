# luhn

Validates whether a string contains a valid credit card number using the Luhn checksum algorithm. Non-numeric characters (hyphens, spaces) are stripped before validation. Returns `true` for valid card numbers, `false` otherwise.

## Syntax

```fuseql
| luhn(<string>) as <alias>
```

## Parameters

| Parameter | Required | Description |
|---|---|---|
| `<string>` | Yes | A string field or literal containing a potential credit card number. |
| `as <alias>` | Yes | Name for the boolean output column. |

## Example

Check whether a known Luhn-valid test card number passes validation.

```fuseql
source="nginx"
| parse "* - - [*] \"* *\" * * *" as ip,date,method,url,status,bytes,rest
| luhn("4532015112830366") as is_valid_card
| first(is_valid_card)
```

**Expected output:**

| first(is_valid_card) |
|---|
| True |

### API Call

```bash
curl -s -X POST "https://<kloudfuse-hostname>/query" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ getLogMetricsResultWithKfuseQl(query: \"source=\\\"nginx\\\" | parse \\\"* - - [*] \\\\\\\"* *\\\\\\\" * * *\\\" as ip,date,method,url,status,bytes,rest | luhn(\\\"4532015112830366\\\") as is_valid_card | first(is_valid_card)\", startTs: \"<ISO_START>\", endTs: \"<ISO_END>\") { ColumnHeaders AggrValues GroupKeys TableResult } }"}'
```

## Notes

- `4532015112830366` is a standard Luhn-valid test number with no real financial value.
- Use `luhn` for PCI compliance scanning: apply it to log fields that might contain card data to detect accidental logging of payment information.
- Non-numeric characters (spaces, hyphens) are stripped before the check, so both `"4532-0151-1283-0366"` and `"4532015112830366"` produce the same result.
