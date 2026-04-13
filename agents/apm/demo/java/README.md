# APM Demo — Java

A minimal Java application instrumented with the **OpenTelemetry Java agent** (zero-code / automatic instrumentation).
Traces are exported via OTLP/HTTP to `https://steve-dev-gcp.kloudfuse.io/ingester/otlp/traces`.

## How it works

The manifest has two stages:

1. **Init container** (`busybox`) — downloads the latest `opentelemetry-javaagent.jar`
   (~23 MB) from the official GitHub release into a shared `emptyDir` volume.

2. **Main container** (`eclipse-temurin:21-jdk-alpine`) — writes `DemoServer.java`
   to disk, compiles it against the javaagent jar (which exposes `io.opentelemetry.api.*`),
   then runs it with:
   ```
   java -javaagent:/agent/opentelemetry-javaagent.jar -cp /app DemoServer
   ```

The agent initializes `GlobalOpenTelemetry` at JVM startup. The application then
obtains a `Tracer` via `GlobalOpenTelemetry.getTracer()` and runs a **1-second trace loop**:

1. A root `"database"` span with `SpanKind = SERVER` is started and made current.
2. A child `"user"` span with `SpanKind = CLIENT` is started within the active scope,
   so both spans share the same trace ID.
3. The child span ends after ~50 ms; the parent span ends immediately after.
4. The loop sleeps for ~950 ms before repeating.

## Prerequisites

- `kubectl` configured against the `dev_gcp` context
- A Kloudfuse Ingestion API key (see **Administration → API Keys** in the Kloudfuse UI)
- Outbound internet access from the cluster (init container downloads the agent JAR from GitHub)

## How traces reach Kloudfuse

In this deployment the Kloudfuse stack runs directly in the cluster. Traces are
sent via **OTLP/HTTP** (port 443) through the nginx ingress to the `ingester` service:

```
pod → https://steve-dev-gcp.kloudfuse.io/ingester/otlp/traces → ingester:8090
```

> **Note:** A standalone `kf-agent` on port 4317/4318 is not deployed in this cluster.
> OTLP/gRPC to port 4317 will be refused — use the HTTPS ingress path above.

The pod uses `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` (not the base
`OTEL_EXPORTER_OTLP_ENDPOINT`) because it sets the exact URL without the agent
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

The Java agent reads `OTEL_EXPORTER_OTLP_HEADERS` automatically — no code changes needed.

## Deploy

```bash
kubectl apply --context dev_gcp -n steve -f manifest.yaml
```

## Check the pod is ready

First startup takes ~60 s (agent download + Java compilation). Monitor progress:

```bash
# Watch init container download the agent
kubectl logs apm-demo-java --context dev_gcp -n steve -c otel-agent-init -f

# Then watch the main container start
kubectl logs apm-demo-java --context dev_gcp -n steve -c java-app -f
```

Wait until you see:
```
demo-java-service starting trace loop (1 trace/second)
```

Check overall pod status:
```bash
kubectl get pod apm-demo-java --context dev_gcp -n steve
```

## Verify traces in Kloudfuse

1. Open **Kloudfuse UI → APM → Trace Explorer**
2. Filter: `service.name = demo-java-service`
3. You should see one trace per second, each containing two spans:
   - `database` — `SpanKind = SERVER` (root span)
   - `user` — `SpanKind = CLIENT` (child span, same trace ID)
   - Resource attributes: `deployment.environment.name = dev`, `service.namespace = apm-demo`
4. The service should appear in **APM → Service Map** with request throughput and latency
   metrics (driven by the `SERVER` span kind)

To confirm the agent is active, check for agent startup messages in the logs:

```bash
kubectl logs apm-demo-java --context dev_gcp -n steve -c java-app | grep -i "opentelemetry"
```

You should see lines like:
```
[otel.javaagent 2024-...] INFO ... - opentelemetry-javaagent - version: 2.x.x
```

## Key OTel configuration

| Setting | Value |
|---------|-------|
| Service name | `demo-java-service` |
| Exporter | OTLP/HTTP |
| Endpoint | `https://steve-dev-gcp.kloudfuse.io/ingester/otlp/traces` |
| Protocol | `http/protobuf` |
| Compression | gzip |
| Authentication | `kf-api-key` header via `OTEL_EXPORTER_OTLP_HEADERS` (from Secret `kloudfuse-api-key`) |
| Spans emitted | `database` (SERVER, root) → `user` (CLIENT, child) |
| Emit rate | 1 trace/second |
| Sampler | `parentbased_traceidratio` at `1.0` (100%) |
| Instrumentation | Manual API — `GlobalOpenTelemetry.getTracer()` + explicit `SpanKind` |
| Agent logging | Routed to application logger (`OTEL_JAVAAGENT_LOGGING=application`) |

## Tear down

```bash
kubectl delete pod apm-demo-java --context dev_gcp -n steve
```
