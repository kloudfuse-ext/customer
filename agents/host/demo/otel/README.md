# Host Demo — OTel Collector

Installs the **OpenTelemetry Collector Contrib** directly on a standalone host or VM
(e.g. AWS EC2, GCP instance, Azure VM).
The collector receives OTLP telemetry from the `host-demo` pod and also scrapes host-level
metrics (CPU, memory, disk, network) from the local OS via the `hostmetrics` receiver.
All three signals — metrics, logs, and traces — are forwarded to Kloudfuse over OTLP HTTP.

The `host-demo` pod (from `../manifest.yaml`) runs with `hostNetwork: true` and sends metrics, logs,
and traces via OTLP HTTP to `http://localhost:4318`, where the OTel Collector listens.

## How it works

- The OTel Collector Contrib is installed as a system service on the host — not as a Kubernetes DaemonSet.
- The `otlp` receiver accepts traces, metrics, and logs from the demo pod on `localhost:4317` (gRPC) and `localhost:4318` (HTTP).
- The `hostmetrics` receiver collects CPU, memory, disk, filesystem, network, and load metrics from the host OS every 30 seconds.
- The `resourcedetection` processor auto-detects host identity (hostname, cloud provider, region, instance ID) from EC2/GCP/Azure metadata APIs.
- `kf_platform: host` is a required resource attribute — Kloudfuse uses it to correlate APM traces with host infrastructure metrics.
- `kf_metrics_agent: otlp` enables the *Infra* tab on APM service detail pages.
- All signals are exported to `https://<kloudfuse-hostname>/ingester/otlp/*` via OTLP HTTP.

## Prerequisites

- SSH access to the target host.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the `Kf-Api-Key` header.

## Install the OTel Collector

Run the following on the host to install the OTel Collector Contrib:

```bash
# Download and install (Linux x86_64 — adjust for your architecture)
OTEL_VERSION="0.115.0"
wget -q "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${OTEL_VERSION}/otelcol-contrib_${OTEL_VERSION}_linux_amd64.deb"
sudo dpkg -i "otelcol-contrib_${OTEL_VERSION}_linux_amd64.deb"
```

For RPM-based systems (Amazon Linux, RHEL):
```bash
OTEL_VERSION="0.115.0"
wget -q "https://github.com/open-telemetry/opentelemetry-collector-releases/releases/download/v${OTEL_VERSION}/otelcol-contrib_${OTEL_VERSION}_linux_amd64.rpm"
sudo rpm -ivh "otelcol-contrib_${OTEL_VERSION}_linux_amd64.rpm"
```

See the [OTel Collector installation docs](https://opentelemetry.io/docs/collector/installation/#linux) for all options.

## Configure the collector

Replace `<kloudfuse-hostname>` and `<token>` in `config.yaml`, then deploy:

```bash
sudo cp config.yaml /etc/otelcol-contrib/config.yaml
sudo systemctl restart otelcol-contrib
sudo systemctl enable otelcol-contrib
```

## Deploy the demo pod

```bash
# Replace <namespace> in manifest.yaml, then:
kubectl apply -f ../manifest.yaml
```

The pod uses `hostNetwork: true` so `localhost` resolves to the node's network interface,
where the OTel Collector is listening on port 4318.

## Verify in Kloudfuse

**Host metrics** — collected by `hostmetrics` receiver, appear immediately after collector start:
```
system.cpu.utilization
system.memory.utilization
system.disk.io
system.filesystem.utilization
system.network.io
```

**Application metrics** — emitted by the demo pod, forwarded via OTLP:
```
demo_requests_total
demo_errors_total
demo_active_connections
demo_request_duration_seconds
```

**Logs** — structured JSON logs from the demo pod appear in the Kloudfuse Logs explorer:
```
service="host-demo" level=INFO
service="host-demo" level=WARNING
service="host-demo" level=ERROR
```

**Traces** — appear in APM > Services as `host-demo`:
```
service="host-demo" span.name="handle_request"
service="host-demo" span.name="db_query"
```

Filter by `kf_platform="host"` to distinguish host telemetry from Kubernetes workloads.

## Tear down

```bash
# Remove the demo pod
kubectl delete -f ../manifest.yaml

# Stop and remove the OTel Collector from the host
sudo systemctl stop otelcol-contrib
sudo dpkg -r otelcol-contrib     # Debian/Ubuntu
# or
sudo rpm -e otelcol-contrib      # RHEL/Amazon Linux
```

## External References

- [OTel Collector — Installation](https://opentelemetry.io/docs/collector/installation/)
- [OTel Collector — hostmetrics receiver](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/receiver/hostmetricsreceiver)
- [Kloudfuse Docs — OTel Collector on a Host](https://docs.kloudfuse.com/platform/latest/data-collection/otel/host)
