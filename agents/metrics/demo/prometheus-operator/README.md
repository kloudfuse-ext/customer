# Metrics Demo — Prometheus Operator

Deploys **Prometheus Operator** and Prometheus using the
`prometheus-community/kube-prometheus-stack` Helm chart. Scrapes the `metrics-demo`
Service through a `ServiceMonitor` and forwards metrics to Kloudfuse via the
Prometheus remote write protocol.

[`prometheus-cr.yaml`](prometheus-cr.yaml) shows the same remote write configuration on a
`Prometheus` custom resource, for clusters that run Prometheus Operator without the chart.

Docs: `kf-docs` → `pages/integration/misc/prometheus.adoc`, sections
*kube-prometheus-stack Helm Chart* and *Prometheus CRD*.

## How it works

- The `ServiceMonitor` in [`servicemonitor.yaml`](servicemonitor.yaml) selects the `metrics-demo` Service.
  Its `release: kube-prometheus-stack` label matches the chart's default `serviceMonitorSelector`.
- Prometheus forwards scraped metrics to `https://<kloudfuse-hostname>/ingester/write` via remote write.
- In the `Prometheus` resource, `remoteWrite[].authorization.credentials` is a **Secret key
  reference** (`name` and `key`), not the token. A plain string is rejected by the API server:
  `spec.remoteWrite[0].authorization.credentials ... must be of type object: "string"`.
  The operator reads the Secret and renders it into `prometheus.yml` as a Bearer token.

## Prerequisites

- Helm 3 installed.
- The `metrics-demo` pod from [`../metric-emitter/`](../metric-emitter/) deployed and running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key. If it is not, remove the
  `authorization` block from the values file and skip the Secret.

## Deploy — kube-prometheus-stack

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

kubectl create namespace monitoring
kubectl -n monitoring create secret generic kloudfuse-ingest --from-literal=token=<token>

# Replace <kloudfuse-hostname> and <NODE_LABEL> in helm-values.yaml first, then:
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -f helm-values.yaml \
  --namespace monitoring

# Replace <NAMESPACE> with the metrics-demo namespace, then:
kubectl apply -f servicemonitor.yaml
```

## Deploy — Prometheus custom resource only

Requires Prometheus Operator and its CRDs to be installed already.

```bash
kubectl -n monitoring create secret generic kloudfuse-ingest --from-literal=token=<token>

# Replace <kloudfuse-hostname> and <NODE_LABEL> in prometheus-cr.yaml first, then:
kubectl apply -f prometheus-cr.yaml
kubectl apply -f servicemonitor.yaml
```

If you deploy both, each Prometheus scrapes `metrics-demo` and sends its own copy, told
apart by the `prometheus` label (`monitoring/kube-prometheus-stack-prometheus` or
`monitoring/prometheus-kloudfuse`).

## Verify

Check remote write from inside the cluster:

```bash
kubectl -n monitoring port-forward svc/kube-prometheus-stack-prometheus 9090:9090
curl -s localhost:9090/api/v1/query --data-urlencode 'query=sum(prometheus_remote_storage_samples_total)'
curl -s localhost:9090/api/v1/query --data-urlencode 'query=sum(prometheus_remote_storage_samples_failed_total)'
```

Then in Kloudfuse, metrics from `metrics-demo` arrive with the ServiceMonitor's labels:

```
demo_requests_total{job="metrics-demo", namespace="$NAMESPACE", service="metrics-demo"}
demo_active_connections{job="metrics-demo", prometheus="monitoring/kube-prometheus-stack-prometheus"}
```

## Tear down

```bash
kubectl delete -f servicemonitor.yaml
kubectl delete -f prometheus-cr.yaml --ignore-not-found
helm uninstall kube-prometheus-stack -n monitoring
kubectl -n monitoring delete secret kloudfuse-ingest
```

The chart's CRDs stay installed after `helm uninstall`; remove them with
the following if no other Prometheus Operator installation uses them:

```bash
kubectl get crd -o name | grep monitoring.coreos.com | xargs kubectl delete
```
