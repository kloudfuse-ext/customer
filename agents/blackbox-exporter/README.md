# Synthetic Monitoring — Prometheus Blackbox Exporter

Runs HTTP, TCP, ICMP, and DNS probes with the
[Prometheus Blackbox Exporter](https://github.com/prometheus/blackbox_exporter)
and sends the results to Kloudfuse. Three collection methods are included; deploy
one or more:

| Directory | Scraper | Sends to | `job` label |
|---|---|---|---|
| [`prometheus/`](prometheus/) | Prometheus (`prometheus-community/prometheus`) | `/ingester/write` | `blackbox-http`, `blackbox-tcp`, `blackbox-icmp`, `blackbox-dns` |
| [`prometheus-operator/`](prometheus-operator/) | kube-prometheus-stack — chart ServiceMonitors and a `Probe` resource | `/ingester/write` | `blackbox-prometheus-blackbox-exporter` (ServiceMonitor), `probe/monitoring/public-endpoints` (Probe) |
| [`otel/`](otel/) | OpenTelemetry Collector, single-replica Deployment | `/ingester/otlp/metrics` | `otel-blackbox-http` |

Docs: `kf-docs` → Reference → Instrumentation → Synthetic Monitoring
(`pages/reference/instrumentation/prom-blackbox-exporter/`).

## How it works

1. The scraper calls the exporter's `/probe?target=<target>&module=<module>` endpoint once per target per scrape interval.
2. The exporter runs the module's check and answers with `probe_success`, `probe_duration_seconds`, and prober-specific metrics.
3. The scraper copies the target into the `instance` label and forwards the metrics to Kloudfuse.

The target list lives in the scraper; the exporter config ([`blackbox-values.yaml`](blackbox-values.yaml)) only defines modules.

## Prerequisites

- A Kubernetes cluster and Helm 3. Run the exporter outside the Kloudfuse cluster to test the path your users take.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key (see the commented blocks in each values file).
- To run `validate.py`: Python 3 with `requests`, and a Grafana service-account token for the Kloudfuse cluster.

## Deploy

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# 1. Exporter
helm upgrade --install blackbox prometheus-community/prometheus-blackbox-exporter \
  -f blackbox-values.yaml --namespace monitoring --create-namespace

# 2a. Prometheus
sed "s/<kloudfuse-hostname>/$KLOUDFUSE_HOST/g" prometheus/helm-values.yaml > /tmp/prom.yaml
helm upgrade --install prometheus-blackbox prometheus-community/prometheus \
  -f /tmp/prom.yaml --namespace monitoring

# 2b. OpenTelemetry Collector
sed "s/<kloudfuse-hostname>/$KLOUDFUSE_HOST/g" otel/helm-values.yaml > /tmp/otel.yaml
helm upgrade --install otel-blackbox open-telemetry/opentelemetry-collector \
  -f /tmp/otel.yaml --namespace monitoring

# 2c. Prometheus Operator (kube-prometheus-stack + chart ServiceMonitors + Probe)
sed "s/<kloudfuse-hostname>/$KLOUDFUSE_HOST/g" prometheus-operator/kube-prometheus-stack-values.yaml > /tmp/kps.yaml
sed "s/<kloudfuse-hostname>/$KLOUDFUSE_HOST/g" prometheus-operator/blackbox-servicemonitor-values.yaml > /tmp/sm.yaml
helm upgrade --install kube-prometheus-stack prometheus-community/kube-prometheus-stack \
  -f /tmp/kps.yaml --namespace monitoring
helm upgrade --install blackbox prometheus-community/prometheus-blackbox-exporter \
  -f blackbox-values.yaml -f /tmp/sm.yaml --namespace monitoring
kubectl apply -f prometheus-operator/probe.yaml
```

### Authenticated endpoints (optional)

[`blackbox-auth-values.yaml`](blackbox-auth-values.yaml) adds an `http_bearer` module that
reads a Bearer token from a mounted Secret:

```bash
kubectl -n monitoring create secret generic blackbox-probe-auth --from-literal=token=<bearer-token>
helm upgrade --install blackbox prometheus-community/prometheus-blackbox-exporter \
  -f blackbox-values.yaml -f blackbox-auth-values.yaml --namespace monitoring
```

This token is sent to the endpoint under test. The token for Kloudfuse belongs in the
scraper's remote write / OTLP exporter config.

## Test a probe by hand

```bash
kubectl -n monitoring port-forward svc/blackbox-prometheus-blackbox-exporter 9115:9115
curl "http://localhost:9115/probe?target=https://example.com&module=http_2xx&debug=true"
```

Expected results with the demo targets:

| Target | Module | `probe_success` |
|---|---|---|
| `https://example.com` | `http_2xx` | 1 |
| `https://httpbin.org/status/200` | `http_2xx` | 1 |
| `https://does-not-exist.invalid` | `http_2xx` | 0 (fails on purpose) |
| `<kloudfuse-hostname>:443` | `tcp_connect` | 1 |
| `8.8.8.8` | `icmp` | 1 |
| `8.8.8.8:53` | `dns_a` | 1 |
| `https://httpbin.org/bearer` | `http_2xx` / `http_bearer` | 0 (401) / 1 |

## Verify in Kloudfuse

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=glsa_...
python3 validate.py
```

`validate.py` queries Kloudfuse for each method's `job` and checks that every expected
target is present with the expected `probe_success` value. Pass `--only prometheus`,
`--only otel`, or `--only operator` to check one method.

Or, in the Kloudfuse UI: **Metrics → Explorer**, query `probe_success`, filter by `job`.

## Notes from validation

- **ICMP**: the chart runs the exporter as UID 1000 with all capabilities dropped, so
  adding `NET_RAW` alone fails with `socket: operation not permitted`. The values file
  sets the `net.ipv4.ping_group_range` sysctl instead, which keeps the exporter non-root.
- **OTel labels**: the Collector's `prometheus` receiver moves `job`/`instance` to the
  `service.name`/`service.instance.id` resource attributes (`service_name` and
  `service_instance_id` in Kloudfuse) and splits URL targets into bogus
  `server_address="https"` / `server_port="//example.com"` labels. `otel/helm-values.yaml`
  restores `job` and `instance` and drops those labels.
- **Exporter down**: `up{job=...}` drops to 0 and `probe_success` stops reporting — it does
  not report 0. Alert on `up` as well as `probe_success`.
- **Scrape timeout**: the exporter stops a probe at the shorter of the module `timeout`
  and the scrape timeout minus 0.5 s.
- **kind on a proxied workstation**: if `kind create cluster` inherits `HTTP(S)_PROXY`
  pointing at `127.0.0.1`, image pulls fail inside the node. Create the cluster with those
  variables unset.

## Tear down

```bash
kubectl delete -f prometheus-operator/probe.yaml --ignore-not-found
helm uninstall kube-prometheus-stack otel-blackbox prometheus-blackbox blackbox -n monitoring
kubectl -n monitoring delete secret blackbox-probe-auth --ignore-not-found
```
