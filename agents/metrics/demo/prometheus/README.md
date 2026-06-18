# Metrics Demo — Prometheus

Deploys **Prometheus** as a Kubernetes Deployment using the `prometheus-community/prometheus`
Helm chart. Scrapes the `metrics-demo` pod and forwards all metrics to Kloudfuse via
the Prometheus remote write protocol.

## How it works

- Prometheus scrapes all pods annotated with `prometheus.io/scrape: "true"` — including `metrics-demo`.
- Scraped metrics are batched and forwarded to `https://<kloudfuse-hostname>/ingester/write` via remote write.
- Native histograms are enabled (requires Prometheus 2.40+ and Kloudfuse 3.4.3+).

## Prerequisites

- Helm 3 installed.
- The `metrics-demo` pod from [`../metric-emitter/`](../metric-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the `authorization` block.

## Deploy

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Replace <kloudfuse-hostname> and <token> in helm-values.yaml first, then:
helm upgrade --install prometheus prometheus-community/prometheus \
  -f helm-values.yaml \
  --namespace prometheus \
  --create-namespace
```

## Verify metrics in Kloudfuse

Metrics from the `metrics-demo` pod arrive with their Prometheus metric names and
the relabeled `kubernetes_namespace` and `kubernetes_pod_name` labels:

```
demo_requests_total{kubernetes_namespace="$NAMESPACE", kubernetes_pod_name="metrics-demo"}
demo_active_connections{kubernetes_namespace="$NAMESPACE"}
demo_request_duration_seconds{kubernetes_namespace="$NAMESPACE"}
demo_errors_total{kubernetes_namespace="$NAMESPACE"}
```

## Tear down

```bash
helm uninstall prometheus -n prometheus
```
