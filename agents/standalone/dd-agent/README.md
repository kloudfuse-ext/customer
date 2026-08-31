# Standalone Host Demo — Datadog Agent

Installs the **Datadog Agent as the `datadog-agent` systemd service** on a
standalone host (bare metal, VM, or a systemd-enabled container) and points it
at Kloudfuse — the "stand-alone system" install path.

Validated end-to-end against a live Kloudfuse cluster: host metrics arrive
(**389 series / 180 metric names** for `standalone-demo-host` in the validation
run). It was exercised inside an amd64 `systemd`-enabled container to mimic a host.

## How it works

- The official install script installs the Agent and registers `datadog-agent.service`.
- `DD_URL` passed to the install script is written to `dd_url` in `/etc/datadog-agent/datadog.yaml`.
- `datadog.yaml` (this directory) is the validated config: metrics via the v2
  series endpoint, container/host logs over HTTP, TLS validation skipped for dev certs.

## Prerequisites

- A Linux host (or a `--privileged`, systemd-enabled container) with `systemctl`.
- `curl` and root/sudo.
- The external hostname of your Kloudfuse cluster.
- Agent version **7.41+** (the install script pulls the latest 7.x).

## Install

```bash
# 1. Install the Agent as a systemd service (writes dd_url from DD_URL):
DD_API_KEY=kloudfuse \
DD_URL="https://<kloudfuse-hostname>/ingester" \
DD_SITE="datadoghq.com" \
DD_AGENT_MAJOR_VERSION=7 \
bash -c "$(curl -L https://install.datadoghq.com/scripts/install_script_agent7.sh)"

# 2. Replace the generated config with the validated one (edit <kloudfuse-hostname> first):
sudo cp datadog.yaml /etc/datadog-agent/datadog.yaml
sudo chown dd-agent:dd-agent /etc/datadog-agent/datadog.yaml
sudo chmod 640 /etc/datadog-agent/datadog.yaml

# 3. Restart and check the service:
sudo systemctl restart datadog-agent
sudo systemctl is-active datadog-agent
sudo datadog-agent status | grep -A2 "Last Successful"
```

> **Note:** `skip_ssl_validation: true` is set because dev clusters often present
> a self-signed or expired certificate. Remove it to enforce TLS validation.

## Verify

Metrics (Prometheus datasource) — expect a non-zero series count for the host:

```bash
curl -sk -G -H "Authorization: Bearer $GRAFANA_TOKEN" \
  --data-urlencode 'query=count({host="standalone-demo-host"})' \
  "https://<kloudfuse-hostname>/grafana/api/datasources/proxy/uid/<prometheus-uid>/api/v1/query"
```

Or in the Kloudfuse UI: **Metrics** → filter `host = standalone-demo-host`.

## Tear down

```bash
sudo systemctl stop datadog-agent
sudo apt-get remove -y datadog-agent   # or: sudo yum remove datadog-agent
```
