# Logs Demo — Log Emitter

A minimal pod that continuously writes **structured JSON logs** to stdout at 1 line/second.
Log agents running as DaemonSets on the same node collect these from `/var/log/containers/` and
forward them to Kloudfuse.

## What it emits

The pod cycles through seven log records covering all three severity levels:

| Level | Message | Key fields |
|-------|---------|------------|
| INFO | request completed | `status=200`, `latency_ms=12` |
| WARN | slow response detected | `status=200`, `latency_ms=452` |
| ERROR | upstream timeout | `status=503`, `latency_ms=5001` |
| INFO | cache hit | `status=200`, `latency_ms=3` |
| WARN | rate limit approaching | `status=200`, `latency_ms=87` |
| INFO | user authenticated | `status=200`, `latency_ms=34` |
| ERROR | database connection lost | `status=500`, `latency_ms=2` |

Each record also includes `timestamp`, `service`, `pod`, `namespace`, `counter`, `method`, and `path`.

## Deploy

```bash
kubectl apply -f manifest.yaml
```

## Verify logs are being emitted

```bash
kubectl logs logs-demo -n $NAMESPACE -f
```

Expected output:
```
logs-demo starting log loop (1 log/second)
{"timestamp": "2026-05-27T...", "level": "INFO", "message": "request completed", "service": "logs-demo", ...}
{"timestamp": "2026-05-27T...", "level": "WARN", "message": "slow response detected", ...}
```

## Next steps

Deploy one of the agent configs to collect and forward these logs to Kloudfuse.
All agents collect from the same `/var/log/containers/` path on the node:

| Agent | Store in Kloudfuse | Key filter |
|-------|--------------------|------------|
| [`../dd-agent/`](../dd-agent/) | Logs | `source="logs-demo"` |
| [`../otel/`](../otel/) | Logs | `k8s.namespace.name="$NAMESPACE"` |
| [`../filebeat/`](../filebeat/) | Logs | `source="filebeat"` |
| [`../fluentd/`](../fluentd/) | Logs | `source="fluentd"` |
| [`../elastic/`](../elastic/) | Logs | `source="filebeat"` (same endpoint) |

## Tear down

```bash
kubectl delete pod logs-demo -n $NAMESPACE
```
