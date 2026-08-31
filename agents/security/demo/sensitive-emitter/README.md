# Security Demo — Sensitive-Data Emitter

A minimal pod that continuously writes **structured JSON logs** to stdout at 1 line/second,
where each record carries a value the masking rules must redact — plus decoys they must
leave alone. Log agents running as DaemonSets on the same node collect these from
`/var/log/containers/` and (with the masking config) forward the redacted lines to Kloudfuse.

> **Safety:** every card number below is a public, non-live **test** PAN. No real
> cardholder data is used, and none should ever be added.

## What it emits

| Message | Sensitive field(s) | Expected after masking |
|---------|--------------------|------------------------|
| payment authorized | `pan=4111111111111111` (Visa), `cvv=123` | `[CARD REDACTED]`, `cvv":"[CSC REDACTED]` |
| payment authorized | `pan=5555 5555 5555 4444` (MC), `cvc2` | `[CARD REDACTED]`, `[CSC REDACTED]` |
| payment authorized | `pan=3782 822463 10005` (Amex 15), `cid` | `[CARD REDACTED]`, `[CSC REDACTED]` |
| payment authorized | `pan=6011-0009-9013-9424` (Discover), `cvv2` | `[CARD REDACTED]`, `[CSC REDACTED]` |
| terminal read | `track2=;4111…?`, `service_code` | `[CSC REDACTED]` (incl. leading `;` sentinel) |
| user login | `password`, email `jane.doe+test@example.com` | `[SECRET REDACTED]`, `***@***.***` |
| service call | `authorization: bearer=…`, `api_key` | `[SECRET REDACTED]` |
| audit note (decoy) | prose "the password was reset…" | **unchanged** (no `:`/`=` after the word) |
| order shipped (decoy) | `order_id=ORD-77`, `trace_id` | **unchanged** |

Each record also includes `timestamp`, `level`, `service`, `pod`, `namespace`, `counter`.

## Deploy

```bash
# Replace <NAMESPACE> and <NODE_LABEL> first (or use sed as in the top-level README).
kubectl apply -f manifest.yaml
```

## Verify it is emitting

```bash
kubectl logs security-demo -n <NAMESPACE> -f
```

Expected (raw, before any agent masking):
```
security-demo starting log loop (1 log/second)
{"timestamp": "...", "level": "INFO", "message": "payment authorized", "pan": "4111111111111111", "cvv": "123", ...}
```

## Next steps

Deploy one masking agent to collect and redact these logs:

| Agent | Store in Kloudfuse | Selector |
|-------|--------------------|----------|
| [`../dd-agent/`](../dd-agent/) | Logs | `source="security-demo"` |
| [`../otel/`](../otel/) | Logs | `{service_name="security-demo"}` |

Then run [`../verify.sh`](../verify.sh) to confirm the placeholders arrive and the raw
values do not.

## Tear down

```bash
kubectl delete pod security-demo -n <NAMESPACE>
```
