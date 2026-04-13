# APM Demo — Python

A minimal Python application instrumented with the **OpenTelemetry Python SDK**.
Traces are exported via OTLP/HTTP to `https://<KFUSE_CLUSTER_DNS>/ingester/otlp/traces`.

## How it works

The manifest uses `python:3.12-slim`. On first start the container:

1. Runs `pip install` to get the OTel SDK and OTLP HTTP exporter.
2. Writes `app.py` to disk.
3. Launches `python /app.py` directly (no `opentelemetry-instrument` wrapper needed).

The SDK is initialized programmatically in `app.py`. The application then runs a
**1-second trace loop**:

1. A root `"database"` span with `SpanKind = SERVER` is started via `start_as_current_span`.
2. A child `"user"` span with `SpanKind = CLIENT` is started inside the parent's context
   manager, so both spans share the same trace ID.
3. The child span ends after ~50 ms (when its `with` block exits); the parent ends immediately after.
4. The loop sleeps for ~1 second before repeating.

## Prerequisites

- `kubectl` configured against the `dev_gcp` context
- A Kloudfuse Ingestion API key (see https://docs.kloudfuse.com/platform/latest/administration/authentication/ingestion-api-key/)

## How traces reach Kloudfuse

In this deployment the Trace application is sending SPANS directly to the cluster. Traces are
sent via **OTLP/HTTP** (port 443)

> **Note:** A standalone `kf-agent` on port 4317/4318 is not deployed in this cluster.
> OTLP/gRPC to port 4317 will be refused — use the HTTPS ingress path above.

The pod uses `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` (not the base
`OTEL_EXPORTER_OTLP_ENDPOINT`) because it sets the exact URL without the SDK
appending a `/v1/traces` suffix.

## Create the API key Secret

The manifest injects the Secret's `value` key verbatim into the
`OTEL_EXPORTER_OTLP_HEADERS` environment variable. The OTel exporter expects
that variable to be a complete `name=value` header expression, so the Secret
must store the **full header string**, not just the raw token:

```bash
kubectl create secret generic kloudfuse-api-key \
  --from-literal=value="kf-api-key=<your-api-key>"
```

For example, if your API key is `abc123xyz`, the Secret value should be:
```
kf-api-key=abc123xyz
```

The HTTP exporter reads `OTEL_EXPORTER_OTLP_HEADERS` automatically — no code changes needed.

## Deploy

```bash
kubectl apply -f manifest.yaml
```

## Check the pod is ready

First startup takes ~30 s while `pip install` runs. Watch the logs:

```bash
kubectl logs apm-demo-python -f
```

Wait until you see:
```
demo-python-service starting trace loop (1 trace/second)
```

Check overall pod status:
```bash
kubectl get pod apm-demo-python
```

## Verify traces in Kloudfuse

1. Open **Kloudfuse UI → APM → Trace Explorer**
2. Filter: `service.name = demo-python-service`
3. You should see one trace per second, each containing two spans:
   - `database` — `SpanKind = SERVER` (root span)
   - `user` — `SpanKind = CLIENT` (child span, same trace ID)
   - Resource attributes: `deployment.environment.name = dev`, `service.namespace = apm-demo`
4. The service should appear in **APM → Service Map** with request throughput and latency
   metrics (driven by the `SERVER` span kind)

## Key OTel configuration

| Setting | Value |
|---------|-------|
| Service name | `demo-python-service` |
| Exporter | OTLP/HTTP |
| Endpoint | `https://<KFUSE_CLUSTER_DNS>/ingester/otlp/traces` |
| Protocol | `http/protobuf` |
| Authentication | `kf-api-key` header via `OTEL_EXPORTER_OTLP_HEADERS` (from Secret `kloudfuse-api-key`) |
| Spans emitted | `database` (SERVER, root) → `user` (CLIENT, child) |
| Emit rate | 1 trace/second |
| Instrumentation | Manual SDK — `start_as_current_span` with explicit `SpanKind` |

## Tear down

```bash
kubectl delete pod apm-demo-python
```
