# APM Demo — Go

A minimal Go application instrumented with the **OpenTelemetry Go SDK**.
Traces are exported via OTLP/HTTP to `https://<KFUSE_DNS>/ingester/otlp/traces`.

## How it works

The manifest uses `golang:1.23-alpine` as the runtime image. On first start the
container writes `go.mod` and `main.go` to `/demo`, downloads dependencies with
`go mod tidy`, then runs the program with `go run`. The module cache is kept in an
`emptyDir` volume so subsequent pod restarts skip the download step.

The application runs a **1-second trace loop** — no HTTP server is involved:

1. A root `"database"` span with `SpanKind = SERVER` is started.
2. A child `"user"` span with `SpanKind = CLIENT` is started within the same trace
   context, so both spans share the same trace ID.
3. The child span ends after ~50 ms; the parent span ends immediately after.
4. The loop sleeps for ~950 ms before repeating.

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

First startup takes ~90 s (module download + compilation). Watch until `Running`:

```bash
kubectl get pod apm-demo-go -w
```

Confirm the trace loop has started:

```bash
kubectl logs apm-demo-go | grep "starting trace loop"
```

Expected output:
```
demo-go-service starting trace loop (1 trace/second)
```

## Verify traces in Kloudfuse

1. Open **Kloudfuse UI → APM → Trace Explorer**
2. Filter: `service.name = demo-go-service`
3. You should see one trace per second, each containing two spans:
   - `database` — `SpanKind = SERVER` (root span)
   - `user` — `SpanKind = CLIENT` (child span, same trace ID)
4. The service should appear in **APM → Service Map** with request throughput and latency
   metrics (driven by the `SERVER` span kind)

## Key OTel configuration

| Setting | Value |
|---------|-------|
| Service name | `demo-go-service` |
| Exporter | OTLP/HTTP (`otlptracehttp`) |
| Endpoint | `https://<KFUSE_CLUSTER_DNS>/ingester/otlp/traces` |
| Protocol | `http/protobuf` |
| Authentication | `kf-api-key` header via `OTEL_EXPORTER_OTLP_HEADERS` (from Secret `kloudfuse-api-key`) |
| Spans emitted | `database` (SERVER, root) → `user` (CLIENT, child) |
| Emit rate | 1 trace/second |
| Instrumentation | Manual SDK — `tracer.Start()` with explicit `SpanKind` |

> **Note on semconv attribute names:** if you upgrade to `otelhttp` v0.56+ for HTTP
> instrumentation, ensure all `go.opentelemetry.io/otel/*` modules are aligned at
> v1.31+ — mixing versions will cause compile errors.

## Tear down

```bash
kubectl delete pod apm-demo-go
```
