# Security Demo — OpenTelemetry Collector (masking)

Deploys the **OTel Collector Contrib** as a DaemonSet to collect container logs, **mask**
card numbers, card security codes, credentials, and emails **in the collector**, and
forward the redacted logs to Kloudfuse.

> **Note:** for log collection, deploy as a **DaemonSet** (one collector per node reads
> local log files).

## How it works

- The `logsCollection` preset enables a `filelog` receiver reading `/var/log/pods/*/*/*.log`.
- The `kubernetesAttributes` preset enriches each record with pod, namespace, container.
- `transform/mask_sensitive` applies four `replace_pattern` statements (from
  `reference/otel/logs-processing.adoc#mask-pii`) to `body`, each guarded with
  `where IsString(body)` because `replace_pattern` is a silent no-op on map bodies.
- `$$1$$2` (OTTL) echoes the captured key+separator so masked JSON stays valid JSON.
- The processor runs **before** `batch` in the logs pipeline, so redaction happens before
  export to `https://<kloudfuse-hostname>/ingester/otlp/v1/logs`.

## Prerequisites

- Helm 3.
- The `security-demo` pod from [`../sensitive-emitter/`](../sensitive-emitter/) running.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key — replace `<token>` or remove the header.

## Deploy

```bash
helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
helm repo update

# Replace <kloudfuse-hostname>, <token>, and <NODE_LABEL> in helm-values.yaml first, then:
helm upgrade --install otel-security open-telemetry/opentelemetry-collector \
  -f helm-values.yaml \
  --namespace otel \
  --create-namespace
```

## Verify masking in Kloudfuse

Logs are in the **Logs store**. In the UI, filter to the demo pod:

```logql
{service_name="security-demo"}
```

You should see `[CARD REDACTED]`, `[CSC REDACTED]`, `[SECRET REDACTED]`, and `***@***.***`,
and **no** raw PANs or credentials. Or run the automated check with the otel selector:

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=<kloudfuse-token>
../verify.sh '{service_name="security-demo"}'
```

## Tear down

```bash
helm uninstall otel-security -n otel
```
