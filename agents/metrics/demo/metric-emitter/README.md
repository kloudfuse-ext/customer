# Metrics Demo — Metric Emitter

A minimal Python pod that exposes a Prometheus-compatible `/metrics` endpoint on port 8000.
Used as the metrics source for all agents in this demo suite.

## Metrics emitted

| Metric | Type | Labels |
|--------|------|--------|
| `demo_requests_total` | counter | `method`, `status` |
| `demo_request_duration_seconds` | gauge | `method` |
| `demo_active_connections` | gauge | — |
| `demo_errors_total` | counter | `type` |

## Deploy

```bash
kubectl apply -f manifest.yaml
```

## Verify the endpoint

```bash
kubectl port-forward -n $NAMESPACE pod/metrics-demo 8000:8000
curl http://localhost:8000/metrics
```

## Tear down

```bash
kubectl delete -f manifest.yaml
```
