# Metrics Demo — VictoriaMetrics Agent (vmagent)

Deploys **vmagent** using the official VictoriaMetrics OCI Helm chart.
Scrapes the `metrics-demo` pod and forwards all metrics to Kloudfuse via
the Prometheus remote write protocol.

## How it works

- vmagent scrapes all pods annotated with `prometheus.io/scrape: "true"` — including `metrics-demo`.
- Scraped metrics are batched and forwarded to `https://<kloudfuse-hostname>/ingester/write` via Prometheus remote write.
- The chart creates a `ClusterRole` and `ClusterRoleBinding` automatically (`rbac.create: true`).

## Prerequisites

- Helm 3 installed.
- The `metrics-demo` pod from [`../metric-emitter/`](../metric-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the `headers` block.

## Deploy

```bash
# Replace <kloudfuse-hostname> and <token> in helm-values.yaml first, then:
helm upgrade --install vmagent \
  oci://ghcr.io/victoriametrics/helm-charts/victoria-metrics-agent \
  -f helm-values.yaml \
  --namespace victoria \
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

vmagent's own self-monitoring metrics are also forwarded (job `vmagent`):

```
vmagent_remotewrite_requests_total
vmagent_remotewrite_rows_sent_total
```

## Tear down

```bash
helm uninstall vmagent -n victoria
```
