# Metrics Demo — OTel Collector

Deploys the **OpenTelemetry Collector Contrib** as a Kubernetes DaemonSet using the
`open-telemetry/opentelemetry-collector` Helm chart.
Collects kubelet stats and scrapes Prometheus endpoints. Forwards metrics to Kloudfuse over OTLP HTTP.

## How it works

- The `kubeletMetrics` preset collects pod and node metrics from each node's kubelet.
- The `prometheus` receiver scrapes all pods annotated with `prometheus.io/scrape: "true"` — including `metrics-demo`.
- The `resource` processor tags metrics with `kf_metrics_agent=otlp` for Kloudfuse APM correlation.
- Metrics are exported to `https://<kloudfuse-hostname>/ingester/otlp/metrics` via OTLP HTTP.

## Prerequisites

- Helm 3 installed.
- The `metrics-demo` pod from [`../metric-emitter/`](../metric-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the header.

## Deploy

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Replace <kloudfuse-hostname> and <token> in helm-values.yaml first, then:
helm upgrade --install otel-metrics open-telemetry/opentelemetry-collector \
  -f helm-values.yaml \
  --namespace otel \
  --create-namespace
```

## Verify metrics in Kloudfuse

Custom metrics from the `metrics-demo` pod arrive with their original Prometheus metric names:

```
demo_requests_total
demo_active_connections
demo_request_duration_seconds
demo_errors_total
```

Filter by Kubernetes namespace or pod in the Kloudfuse metrics explorer:
```
kf_metrics_agent="otlp"
kubernetes_namespace="steve"
kubernetes_pod_name="metrics-demo"
```

## Tear down

```bash
helm uninstall otel-metrics -n otel
```
