# FuseQL Search Operators

Search operators are used in the **filter expression** before the first `|` pipe. They select which log lines are included in the query.

## Operators

| Operator | Syntax | Description |
|---|---|---|
| `=` | `label="value"` | Exact equality match |
| `!=` | `label!="value"` | Not-equal match |
| `>` | `@facet>number` | Greater than (numeric facets) |
| `>=` | `@facet>=number` | Greater than or equal |
| `<` | `@facet<number` | Less than |
| `<=` | `@facet<=number` | Less than or equal |
| `=~` | `label=~"regex"` | Regex match (RE2) |
| `!~` | `label!~"regex"` | Regex non-match |
| `*~` | `label*~"prefix"` | Starts with prefix |
| `~*` | `label~*"suffix"` | Ends with suffix |
| `**` | `label**"substring"` | Contains substring |
| `and` | `expr and expr` | Logical AND |
| `or` | `expr or expr` | Logical OR |
| `"text"` | `"substring"` | Full-text grep (substring in log body) |
| `!"text"` | `!"substring"` | Exclude grep matches |
| `term` | `word` | Token search (whole words) |
| `!term` | `!word` | Exclude token matches |
| `@facet` | `@facet` | Key exists (facet is present) |
| `==` | `@facet=="value"` | Facet term exact match |
| `!==` | `@facet!=="value"` | Facet term does not match |

## Key Observations

- Multiple label filters must be combined with `and` explicitly — placing two label filters side by side with a space results in a syntax error.
- Numeric facets (auto-extracted numbers) use the `@` prefix: `@_number_1`, `@_number_2`, etc.
- IP facets are auto-extracted as `@_ipv4_address_0`, `@_ipv4_address_1`, etc.

## Examples

### Equality (`=`)

```
source="nginx" | count
```

**API Call:**
```bash
curl -X POST "https://<kloudfuse-hostname>/api/v1/logs/aggregate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "source=\"nginx\" | count", "startTime": "<ISO_START>", "endTime": "<ISO_END>"}'
```

**Expected output:**
| _count |
|--------|
| 65315875 |

### AND (`and`)

```
source="nginx" and kube_deployment="kfuse-ingress-ingress-nginx-controller" and @_number_1=200 | count
```

**Expected output:**
| _count |
|--------|
| 316591 |

### Not Equal (`!=`)

```
source="nginx" and level!="error" | count by level
```

**Expected output:**
| _count | level |
|--------|-------|
| 324409 | info  |

### Regex (`=~`)

```
source="nginx" and kube_deployment=~"kfuse-ingress.*" | count by kube_deployment
```

**Expected output:**
| _count | kube_deployment |
|--------|----------------|
| 323961 | kfuse-ingress-ingress-nginx-controller |
| 2249   | kfuse-ingress-nginx-controller |

### Not Regex (`!~`)

```
source="nginx" and kube_deployment!~"kfuse-ingress-nginx.*" | count by kube_deployment
```

**Expected output:**
| _count | kube_deployment |
|--------|----------------|
| 333922 | kfuse-ingress-ingress-nginx-controller |

### Starts With (`*~`)

```
source="nginx" and kube_deployment*~"kfuse-ingress-ingress" | count by kube_deployment
```

**Expected output:**
| _count | kube_deployment |
|--------|----------------|
| 335481 | kfuse-ingress-ingress-nginx-controller |

### Ends With (`~*`)

```
source="nginx" and kube_deployment~*"nginx-controller" | count by kube_deployment
```

**Expected output:**
| _count | kube_deployment |
|--------|----------------|
| 319201 | kfuse-ingress-ingress-nginx-controller |
| 2052   | kfuse-ingress-nginx-controller |

### Contains (`**`)

```
source="nginx" and kube_deployment**"ingress-ingress" | count by kube_deployment
```

**Expected output:**
| _count | kube_deployment |
|--------|----------------|
| 316505 | kfuse-ingress-ingress-nginx-controller |

### Greater Than (`>`)

```
source="nginx" and @_number_1>200 | count
```

**Expected output:**
| _count |
|--------|
| 942    |

### Greater Than or Equal (`>=`)

```
source="nginx" and @_number_1>=200 | count by @_number_1
```

**Expected output:**
| _count | @_number_1 |
|--------|-----------|
| 328647 | 200 |
| 147    | 302 |
| 54     | 400 |
| 15     | 401 |
| 549    | 403 |
| 149    | 404 |
| ... | ... |

### Less Than (`<`)

```
source="nginx" and @_number_1<300 | count
```

**Expected output:**
| _count |
|--------|
| 324840 |

### Less Than or Equal (`<=`)

```
source="nginx" and @_number_1<=404 | count by @_number_1
```

**Expected output:**
| _count | @_number_1 |
|--------|-----------|
| 316591 | 200 |
| 147    | 302 |
| 51     | 400 |
| 13     | 401 |
| 522    | 403 |
| 134    | 404 |

## Notes

- Numeric facets (`@_number_0` through `@_number_N`) are auto-extracted from log messages. The HTTP status code in nginx logs is typically `@_number_1`.
- All string comparisons are case-sensitive.
- Combining `and` with `or` requires parentheses to control precedence: `(source="nginx" or source="apache") and level="error"`.
