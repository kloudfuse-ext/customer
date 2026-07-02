# FuseQL IP Operators

IP operators are used inside **pipe stages** (after `|`) to validate, classify, and transform IPv4 addresses extracted from log fields.

## Operators

| Operator | Syntax | Description |
|---|---|---|
| `isValidIP` | `isValidIP(field) as alias` | True if the field contains a valid IPv4 or IPv6 address |
| `isPublicIP` | `isPublicIP(field) as alias` | True if the IPv4 address is publicly routable |
| `isPrivateIP` | `isPrivateIP(field) as alias` | True if the IPv4 address is in an RFC 1918 private range |
| `ipv4ToNumber` | `ipv4ToNumber(field) as alias` | Converts an IPv4 address to its 32-bit integer |
| `getCIDRPrefix` | `getCIDRPrefix(field, prefixLen) as alias` | Returns the network prefix for a given CIDR length |
| `compareCIDRPrefix` | `compareCIDRPrefix(ip1, ip2, prefixLen) as alias` | True if two IPs share the same network prefix |
| `maskFromCIDR` | `maskFromCIDR(prefixLen) as alias` | Returns the subnet mask string for a prefix length |

## Examples

### `isValidIP`

Validate whether a known IP string is syntactically valid.

```
source="nginx"
| isValidIP("10.20.15.214") as valid_ip
| count by valid_ip
```

**API Call:**
```bash
curl -X POST "https://<kloudfuse-hostname>/api/v1/logs/aggregate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "source=\"nginx\" | isValidIP(\"10.20.15.214\") as valid_ip | count by valid_ip", "startTime": "<ISO_START>", "endTime": "<ISO_END>"}'
```

**Expected output:**
| valid_ip | _count |
|----------|--------|
| True     | 133504 |

---

### `isPublicIP`

Check whether an IP address is publicly routable.

```
source="nginx"
| isPublicIP("8.8.8.8") as is_public
| count by is_public
```

**Expected output:**
| is_public | _count |
|-----------|--------|
| True      | 124365 |

---

### `isPrivateIP`

Check whether an IP address falls within RFC 1918 private ranges.

```
source="nginx"
| isPrivateIP("10.20.15.214") as is_private
| count by is_private
```

**Expected output:**
| is_private | _count |
|------------|--------|
| True       | 130532 |

---

### `ipv4ToNumber`

Convert an IPv4 address to its 32-bit integer representation.

```
source="nginx"
| ipv4ToNumber("10.20.15.214") as ip_num
| min(ip_num) as min_ip, max(ip_num) as max_ip
```

**Expected output:**
| min_ip    | max_ip    |
|-----------|-----------|
| 169086934 | 169086934 |

The formula is: `(octet1 × 16,777,216) + (octet2 × 65,536) + (octet3 × 256) + octet4`.
So `10.20.15.214` = `(10 × 16,777,216) + (20 × 65,536) + (15 × 256) + 214` = `169,086,934`.

---

### `getCIDRPrefix`

Return the /16 network prefix for a given IP address.

```
source="nginx"
| getCIDRPrefix("10.20.15.214", 16) as subnet
| count by subnet
```

**Expected output:**
| subnet    | _count |
|-----------|--------|
| 10.20.0.0 | 205729 |

---

### `compareCIDRPrefix`

Check whether two IP addresses fall within the same /24 subnet.

```
source="nginx"
| compareCIDRPrefix("10.20.15.214", "10.20.15.1", 24) as same_net
| count by same_net
```

**Expected output:**
| same_net | _count |
|----------|--------|
| True     | 198333 |

---

### `maskFromCIDR`

Return the subnet mask string for a /24 network.

```
source="nginx"
| maskFromCIDR(24) as mask
| count
```

**Expected output:**
| _count |
|--------|
| 203641 |

The `mask` computed column contains `"255.255.255.0"` for each row, but `count` aggregates across all rows.

Common mappings:
- `maskFromCIDR(8)` → `"255.0.0.0"`
- `maskFromCIDR(16)` → `"255.255.0.0"`
- `maskFromCIDR(24)` → `"255.255.255.0"`
- `maskFromCIDR(32)` → `"255.255.255.255"`

---

## Notes

- IP operators apply to **string** fields containing dot-decimal IPv4 addresses. Fields that contain IP:port combinations (like `"10.0.0.1:8080"`) will return `false` for `isValidIP`.
- `isPublicIP` and `isPrivateIP` apply to IPv4 only. `isValidIP` also accepts IPv6.
- The `_count` values in examples depend on the query time range — they will differ in production.
- Auto-extracted IPv4 facets (`_ipv4_address_0`, `_ipv4_address_1`) may contain IP:port strings that fail `isValidIP`; parse the log line first to extract a clean IP field.
