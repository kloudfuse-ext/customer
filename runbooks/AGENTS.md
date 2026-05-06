# AGENTS.md — Kloudfuse Customer Runbooks

This file provides guidance for AI agents working in this repository.

## Repository Purpose

This repository contains operational runbooks and scripts for managing and troubleshooting the Kloudfuse observability stack. The stack runs on Kubernetes and includes Apache Pinot, Kafka, ZooKeeper, PostgreSQL, Grafana, and the Kloudfuse agents.

**GitHub:** https://github.com/kloudfuse/customer

---

## Repository Structure

```
customer/
├── runbooks/               # Markdown runbooks for operators
│   ├── alerts/             # Runbooks tied to specific Kloudfuse alerts
│   └── *.md                # General operational runbooks
└── scripts/                # Executable scripts referenced by runbooks
    ├── alerts/             # Scripts used by alert runbooks
    ├── assets/             # Dashboard and alerting framework (Python)
    ├── postgres-backup/    # PostgreSQL backup/restore
    ├── multi-az/           # Multi-AZ switchover
    └── *.sh / *.py         # General operational scripts
```

---

## Runbook Conventions

### Format

Every runbook must follow this structure:

1. `# Title` — matches the alert name or operation
2. `## Table of Contents` — link to every `##` section
3. `## Summary` — what the alert/operation is, impact, common root causes, and namespace note
4. `## Symptoms` — alert PromQL expression and a metrics table (Healthy / Unhealthy values)
5. Numbered `## Step N:` sections — sequential, actionable steps
6. `## Prevention` — how to avoid recurrence
7. `## Related Runbooks` — links to related docs

### Namespace Note

All runbooks include this note in the Summary:

> All commands assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

### Log Queries

When a step requires searching logs, direct the user to **Kloudfuse UI → Logs → Advanced Search** with a FuseQL query. Do not use `kubectl logs` for log searching. Use the following FuseQL conventions:

- Filter by deployment: `kube_deployment="query-service"`
- Filter by statefulset: `kube_stateful_set="pinot-broker"`
- Filter by pod name: `kube_pod="<POD_NAME>"`
- Filter by service: `kube_service="pinot-server"`
- Filter by pod prefix: `kube_pod*~"pinot-server"`
- Filter by level: `level=~"warn|error"` or `__kf_level="ERROR"`
- Keyword search: `("Failed to load" or "Failed to download")`
- Regex match on multiple values: `kube_stateful_set=~"pinot-server-realtime|pinot-server-offline"`
- Combine filters: `kube_stateful_set="pinot-broker" and ("QueryException" or "timeout") and level=~"error|warn"`

Use `kube_pod` for logs from a specific pod (e.g., a pod that has already restarted). Use `kube_deployment` or `kube_stateful_set` for component-wide searches.

### Scripts

Runbooks in `alerts/` reference scripts in `scripts/alerts/`. When a step involves repeated API calls or multi-step operations, use the script rather than inline `kubectl exec` curl commands.

---

## Scripts Reference

### `scripts/alerts/segments-error.sh`

Used by the Pinot segment runbooks. Wraps Pinot Controller REST API calls.

| Command | Purpose |
|---------|---------|
| `./segments-error.sh status [table]` | List all tables with non-ONLINE segments, or check a specific table |
| `./segments-error.sh diagnose <table>` | Show segment states and server assignments (ExternalView) |
| `./segments-error.sh reload <table> [segment]` | Reload all or one segment; rechecks status after 10s |
| `./segments-error.sh reset <table> <segment>` | Reset a REALTIME consuming segment (prompts for confirmation) |
| `./segments-error.sh verify <table>` | Post-recovery check: segment counts, broker query, PromQL queries |

Set `NAMESPACE` env var to override the default `kfuse` namespace.

### `scripts/alerts/resize_pvc.sh`

Resizes a StatefulSet PVC and recreates the StatefulSet with the new storage size.

```bash
./resize_pvc.sh <statefulset-name> <new-size> [namespace]
```

Prompts for confirmation before the destructive StatefulSet delete. Vendor-specific resize constraints (AWS, GCP, Azure) are documented in the [PVC Volume Capacity Alert runbook](alerts/pvc-volume-capacity-alert.md).

---

## Alert Runbooks

| Runbook | Alert / Trigger |
|---------|----------------|
| [alerts/pinot-segments-unavailable.md](alerts/pinot-segments-unavailable.md) | `pinot_controller_percentSegmentsAvailable_Value < 90` |
| [alerts/pinot-segments-in-error-state.md](alerts/pinot-segments-in-error-state.md) | `pinot_controller_segmentsInErrorState_Value > 0` |
| [alerts/pvc-volume-capacity-alert.md](alerts/pvc-volume-capacity-alert.md) | PVC usage exceeds 90% |
| [alerts/node_status.md](alerts/node_status.md) | Node condition not Ready |
| [alerts/node-high-cpu-usage.md](alerts/node-high-cpu-usage.md) | Node CPU usage >= 90% (5m avg) |
| [alerts/kfuse-observability-agents.md](alerts/kfuse-observability-agents.md) | Kloudfuse agent not running on a node |
| [alerts/kfuse-ingest-service-availability.md](alerts/kfuse-ingest-service-availability.md) | Ingest pipeline pods unavailable (envoy, nginx, transformers, Kafka, ingester) |
| [alerts/kfuse-query-service-availability.md](alerts/kfuse-query-service-availability.md) | Query tier pods unavailable (query-service, Pinot controller/broker/server) |
| [alerts/kfuse-user-access-service-availability.md](alerts/kfuse-user-access-service-availability.md) | User-facing pods unavailable (UI, beffe, auth, Grafana, user/config mgmt) |
| [alerts/kfuse-misc-service-availability.md](alerts/kfuse-misc-service-availability.md) | Auxiliary service pods unavailable (vector agents, zapper, configdb, hydration) |
| [alerts/kfuse-zookeeper-quorum-alert.md](alerts/kfuse-zookeeper-quorum-alert.md) | ZooKeeper quorum degraded (pinot-zookeeper replicas unavailable) |

---

## General Runbooks

| Runbook | Topic |
|---------|-------|
| [pinot-zookeeper-corruption-recovery.md](pinot-zookeeper-corruption-recovery.md) | ZooKeeper data corruption recovery |
| [kafka-rebalance.md](kafka-rebalance.md) | Kafka partition rebalancing |
| [custom-retention-partition-increase.md](custom-retention-partition-increase.md) | Increasing Kafka partitions for custom retention |
| [stop-queries-and-ingestion.md](stop-queries-and-ingestion.md) | Stopping queries and ingestion |
| [Scale Up.md](Scale%20Up.md) | Scaling up node instance types |
| [ScaleOut.md](ScaleOut.md) | Scaling out the cluster |
| [aws-cluster-setup.md](aws-cluster-setup.md) | AWS cluster setup |
| [postgres-password-reset.md](postgres-password-reset.md) | PostgreSQL password reset |
| [refresh-servicegrouplist.md](refresh-servicegrouplist.md) | Refreshing service group list |
| [http-check.md](http-check.md) | HTTP endpoint check configuration |
| [Docker_Rate_Limit.md](Docker_Rate_Limit.md) | Docker Hub rate limit resolution |
| [crashloopbackupoff_alert.md](crashloopbackupoff_alert.md) | CrashLoopBackOff pod recovery |
| [imagepullbackoff_alert.md](imagepullbackoff_alert.md) | ImagePullBackOff pod recovery |
| [pod_failed_alert.md](pod_failed_alert.md) | Pod failed / eviction recovery |
| [degraded_deployments.md](degraded_deployments.md) | Degraded deployments and StatefulSets |

---

## Key Configuration References

### JVM Memory Tuning

Different Pinot components use different fields in `charts/kfuse/values.yaml`:

| Component | Field | Format | Example location |
|-----------|-------|--------|-----------------|
| `pinot-zookeeper` | `pinot.zookeeper.heapSize` | integer MB | line ~1598 |
| `pinot-server-realtime` | `pinot.server.realtime.jvmMemory` | string with unit | line ~1711 |
| `pinot-server-offline` | `pinot.server.offline.jvmMemory` | string with unit | line ~1722 |
| `pinot-minion` | `pinot.minion.jvmMemory` | string with unit | line ~1736 |
| `kafka-kraft-broker` | `kafka-kraft.broker.heapOpts` | full JVM flags | line ~1534 |

Example:

```yaml
pinot:
  zookeeper:
    heapSize: 8192        # MB integer, default 4096
  server:
    realtime:
      jvmMemory: "8G"
    offline:
      jvmMemory: "4G"
  minion:
    jvmMemory: "4G"
```

Apply changes with `helm upgrade`. For fine-grained JVM flag control use `jvmOpts` instead of `jvmMemory`.

### Namespace

The default namespace for all Kloudfuse components is `kfuse`. Scripts in `scripts/alerts/` default to this and accept a `NAMESPACE` environment variable override.

---

## Writing New Runbooks

When creating a new alert runbook:

1. Place it in `runbooks/alerts/` if tied to a specific alert, otherwise in `runbooks/`
2. Follow the format described in [Runbook Conventions](#runbook-conventions)
3. Use FuseQL queries (not `kubectl logs`) for log investigation steps
4. Reference `segments-error.sh` for any Pinot segment operations
5. Reference `resize_pvc.sh` for any PVC resize operations
6. Link related runbooks in the `## Related Runbooks` section
7. Add a TOC immediately after the `# Title`
