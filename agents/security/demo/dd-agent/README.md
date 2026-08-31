# Security Demo — Datadog Agent (masking)

Deploys the **Datadog node Agent** as a DaemonSet to collect container logs, **mask**
card numbers, card security codes, credentials, and emails **in the agent**, and forward
the redacted logs to Kloudfuse.

## How it works

- The node agent reads container log files from `/var/log/containers/` on each node.
- `agents.customAgentConfig.logs_config.processing_rules` holds four `mask_sequences`
  rules (the ones from `reference/datadog/log-processing.adoc#mask-pii`). They apply to
  **every** log source the agent collects.
- Each rule runs a Go RE2 regex over the raw log line and replaces matches with the
  placeholder. Credential/CSC rules echo the captured key+separator via `$1$2`, so masked
  JSON stays valid JSON.
- Logs are shipped via HTTP to `<kloudfuse-hostname>:443` (`logs_dd_url`).
- The Cluster Agent is disabled — not required for log collection.

> **Global vs. per-source:** these masks are set globally. A source-level
> `log_processing_rules` block would be **additive** to this global list, not a
> replacement — so do not duplicate these rules in a source config.

## Prerequisites

- Helm 3; Datadog Agent **7.41+** and chart **3.1.10+**.
- The `security-demo` pod from [`../sensitive-emitter/`](../sensitive-emitter/) running.
- The external hostname of your Kloudfuse cluster.

## Deploy

```bash
helm repo add datadog https://helm.datadoghq.com
helm repo update

# Replace <kloudfuse-hostname> and <NODE_LABEL> in helm-values.yaml first, then:
kubectl create namespace datadog-agent
helm upgrade --install datadog-agent datadog/datadog \
  -f helm-values.yaml \
  -n datadog-agent \
  --version 3.65.0
```

> An invalid regex in the global `processing_rules` list stops the **logs** agent from
> starting (`agent status` → `Invalid processing rules`); metrics and traces are
> unaffected. The patterns here are validated in [`../../validate/`](../../validate/).

## Verify masking in Kloudfuse

Logs are in the **Logs store**, source `security-demo`. In the UI:

```
source="security-demo"
```

You should see `[CARD REDACTED]`, `[CSC REDACTED]`, `[SECRET REDACTED]`, and `***@***.***`
in the message bodies, and **no** raw PANs or credentials. Or run the automated check:

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=<kloudfuse-token>
../verify.sh
```

> **Note:** `logs_dd_url` uses `<hostname>:443` (no `/ingester` prefix) — different from
> `dd_url` (metrics/events) which uses `https://<hostname>/ingester`.

## Tear down

```bash
helm uninstall datadog-agent -n datadog-agent
kubectl delete namespace datadog-agent
```
