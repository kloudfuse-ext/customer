# FuseQL Predicate Operators

Predicate operators are used inside **pipe stages** (after `|`) to test field values and return booleans. They are typically used in `where` clauses to filter rows or as boolean columns in computed fields.

## Operators

| Operator | Syntax | Description |
|---|---|---|
| `in` | `where field in ("a", "b", ...)` | True if field equals any listed value |
| `isblank` | `isblank(field) as alias` | True if field is null, empty, or whitespace-only |
| `isempty` | `isempty(field) as alias` | True if field is null or exactly empty string |
| `isnull` | `isnull(field) as alias` | True if field is null or missing |
| `luhn` | `where luhn(field)` | True if field passes the Luhn credit-card checksum |
| `matches` | `where field matches "regex"` | True if field matches a RE2 regular expression |
| `isnumeric` | `isnumeric(field) as alias` | True if field can be parsed as a number |

## Examples

### `in`

Filter log lines where the `level` label is one of a set of values.

```
source="nginx"
| where level in ("info", "warning")
| count by level
```

**API Call:**
```bash
curl -X POST "https://<kloudfuse-hostname>/api/v1/logs/aggregate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "source=\"nginx\" | where level in (\"info\", \"warning\") | count by level", "startTime": "<ISO_START>", "endTime": "<ISO_END>"}'
```

**Expected output:**
| _count | level |
|--------|-------|
| 316858 | info  |

---

### `matches`

Filter log lines where the `level` label matches a regular expression.

```
source="nginx"
| where level matches "inf.*"
| count
```

**Expected output:**
| _count |
|--------|
| 317700 |

---

### `isnull`

Check whether a field is null or missing.

```
source="nginx"
| isnull(level) as is_null
| count by is_null
```

**Expected output:**
| is_null | _count |
|---------|--------|
| False   | 155493 |

---

### `isblank`

Check whether a field is null, empty, or whitespace-only.

```
source="nginx"
| isblank(level) as is_blank
| count by is_blank
```

**Expected output:**
| is_blank | _count |
|----------|--------|
| False    | 145071 |

---

### `isempty`

Check whether a field is null or an empty string.

```
source="nginx"
| isempty(level) as is_empty
| count by is_empty
```

**Expected output:**
| is_empty | _count |
|----------|--------|
| False    | 141834 |

---

### `luhn`

Keep only log lines where a literal test card number passes the Luhn check.

```
source="nginx"
| where luhn("4111111111111111")
| count
```

**Expected output:**
| _count |
|--------|
| 324933 |

---

### `isnumeric`

Check whether a string value can be parsed as a number.

```
source="nginx"
| isNumeric("200") as is_num
| count by is_num
```

**Expected output:**
| is_num | _count |
|--------|--------|
| True   | 133504 |

---

## Notes

- `isblank` ⊃ `isempty` ⊃ `isnull`: blank catches whitespace-only, empty catches zero-length strings, null catches absent fields.
- `matches` uses RE2 syntax. Look-ahead and look-behind are not supported.
- The `in` operator is case-sensitive for strings.
- `luhn` strips non-numeric characters before checking, so `"4111-1111-1111-1111"` and `"4111111111111111"` are equivalent.
