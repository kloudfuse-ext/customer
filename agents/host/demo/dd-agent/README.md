# Host Demo — Datadog Agent

Installs the **Datadog Agent** directly on a standalone host or VM (e.g. AWS EC2, GCP instance, Azure VM).
The agent collects host-level metrics (CPU, memory, disk, network), logs, events, and traces, and
forwards all signals to Kloudfuse.

The `host-demo` pod (from `../manifest.yaml`) runs with `hostNetwork: true` and sends metrics, logs,
and traces via OTLP HTTP to `http://localhost:4318`, where the Datadog Agent's OTel receiver listens.

## How it works

- The Datadog Agent is installed as a system service on the host — not as a Kubernetes DaemonSet.
- Host-level metrics (CPU, memory, disk, network) are collected automatically.
- Logs are forwarded to `https://<kloudfuse-hostname>/ingester` via HTTPS.
- Events (container lifecycle, system events) are forwarded to `https://<kloudfuse-hostname>/ingester`.
- Traces are received from the demo pod via the OTel receiver on `localhost:4318` and forwarded to Kloudfuse.

## Prerequisites

- SSH access to the target host.
- The external hostname of your Kloudfuse cluster.

## Install the Datadog Agent

Run the following on the host. This installs the agent and immediately begins collecting host metrics:

```bash
DD_UPGRADE=true \
DD_API_KEY=kloudfuse \
DD_URL="https://<kloudfuse-hostname>/ingester" \
bash -c "$(curl -L https://s3.amazonaws.com/dd-agent/scripts/install_script_agent7.sh)"
```

## Configure the agent

Replace the default `datadog.yaml` with the example in this directory:

```bash
# Replace <kloudfuse-hostname> in datadog.yaml first, then:
sudo cp datadog.yaml /etc/datadog-agent/datadog.yaml
sudo chown dd-agent:dd-agent /etc/datadog-agent/datadog.yaml
sudo systemctl restart datadog-agent
```

The configuration enables:
- **Metrics** — host metrics forwarded to `https://<kloudfuse-hostname>/ingester` via the v2 series API
- **Logs** — collected from the host and forwarded via HTTPS to `<kloudfuse-hostname>:443`
- **Events** — system and container lifecycle events forwarded to `https://<kloudfuse-hostname>/ingester`
- **Traces** — APM receiver on `localhost:4318` (OTLP HTTP) and `localhost:4317` (OTLP gRPC)

## Deploy the demo pod

```bash
# Replace <namespace> in manifest.yaml, then:
kubectl apply -f ../manifest.yaml
```

The pod uses `hostNetwork: true` so `localhost` resolves to the node's network interface,
where the Datadog Agent OTel receiver is listening on port 4318.

## Verify in Kloudfuse

**Metrics** — host metrics appear immediately after agent start:
```
system.cpu.user
system.mem.used
system.disk.used
system.net.bytes_sent
```

**Logs** — structured JSON logs from the demo pod appear in the Kloudfuse Logs explorer:
```
service="host-demo" level=INFO
service="host-demo" level=WARNING
service="host-demo" level=ERROR
```

**Events** — system events appear in the Kloudfuse Events explorer:
```
source="datadog" host="<your-hostname>"
```

**Traces** — traces from the demo pod appear in APM > Services as `host-demo`:
```
service="host-demo" span.name="handle_request"
```

## Tear down

```bash
# Remove the demo pod
kubectl delete -f ../manifest.yaml

# Stop and remove the Datadog Agent from the host
sudo systemctl stop datadog-agent
sudo apt-get remove datadog-agent -y   # Debian/Ubuntu
# or
sudo yum remove datadog-agent -y       # RHEL/Amazon Linux
```

## External References

- [Datadog Agent — Basic Usage](https://docs.datadoghq.com/agent/basic_agent_usage/)
- [Datadog Agent — Log Collection](https://docs.datadoghq.com/agent/logs/)
- [Datadog Agent — APM Setup](https://docs.datadoghq.com/tracing/setup_overview/)
- [Kloudfuse Docs — Datadog Agent on Host Platforms](https://docs.kloudfuse.com/platform/latest/data-collection/datadog/hosts)
