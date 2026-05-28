# Metrics Demo — Datadog Agent

Deploys the **Datadog Agent** as a Kubernetes DaemonSet using the `datadog/datadog` Helm chart.
Collects Kubernetes infrastructure metrics (kube-state-metrics, kubelet, node) and scrapes
the `metrics-demo` pod's Prometheus endpoint via Autodiscovery.

## How it works

- The Cluster Agent collects kube-state-metrics and cluster-level metadata.
- The Node Agent scrapes each node's kubelet and any pods annotated with `prometheus.io/scrape: "true"`.
- The `metrics-demo` pod carries `ad.datadoghq.com/metric-emitter.checks` for explicit OpenMetrics scraping.
- All metrics are forwarded to `https://<kloudfuse-hostname>/ingester` via the Datadog v2 series API.

## Prerequisites

- Helm 3 installed.
- The `metrics-demo` pod from [`../metric-emitter/`](../metric-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the header.

## Deploy

```bash
helm repo add datadog https://helm.datadoghq.com
helm repo update

# Replace <kloudfuse-hostname> in helm-values.yaml first, then:
helm upgrade --install datadog-metrics datadog/datadog \
  --version 3.65.0 \
  -f helm-values.yaml \
  --namespace datadog-agent \
  --create-namespace
```

## Verify metrics in Kloudfuse

Custom metrics from the `metrics-demo` pod appear with the `demo` namespace prefix (set via Autodiscovery):

```
demo.demo_requests_total
demo.demo_active_connections
demo.demo_request_duration_seconds
demo.demo_errors_total
```

Kubernetes infrastructure metrics appear as standard Datadog metric names:
```
kubernetes.cpu.usage.total
kubernetes.memory.usage
kubernetes_state.pod.ready
```

## Tear down

```bash
helm uninstall datadog-metrics -n datadog-agent
```
