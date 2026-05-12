# Kfuse Misc Service Availability

## Table of Contents

- [Summary](#summary)
- [Affected Components](#affected-components)
- [Symptoms](#symptoms)
- [Step 1: Identify the Affected Component](#step-1-identify-the-affected-component)
- [Step 2: Check Pod Status and Events](#step-2-check-pod-status-and-events)
- [Step 3: Check Logs for Root Cause](#step-3-check-logs-for-root-cause)
- [Step 4: Diagnose Root Cause](#step-4-diagnose-root-cause)
- [Step 5: Restart the Affected Component](#step-5-restart-the-affected-component)
- [Step 6: Post-Recovery Verification](#step-6-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

The misc service availability alerts fire when **1 or more** pods in the Kloudfuse auxiliary services tier become unavailable for **10 minutes**. These services support supplementary features — data hydration, archival, enrichment, cloud integration, and configuration storage. While their failure does not immediately halt core ingestion or query functionality, they affect data completeness, enrichment quality, and system configuration.

**Impact:** Depending on the affected component:
- **hydration-service:** Data hydration for backfill or archival replay stops
- **zapper:** Data retention/TTL enforcement stops; data may not be expired on schedule
- **az-service:** Availability zone–aware routing or metadata enrichment is impacted
- **kf-mcp:** MCP (Model Context Protocol) integrations are unavailable
- **kfuse-archival-vector:** Log/metric archival to long-term storage stops
- **kfuse-enrichment-vector:** Real-time data enrichment (tag injection, field transforms) stops
- **kfuse-rum-vector:** RUM data forwarding stops
- **kfuse-audit-log-vector:** Audit log forwarding stops; compliance records may be incomplete
- **kfuse-cloud-exporter:** Cloud metrics export stops
- **hydration-logs-parser:** Log parsing for hydrated data stops
- **kfuse-configdb:** Configuration database unavailable; auth, user management, and configuration APIs will fail

**Note:** `kfuse-configdb` is a critical dependency for `kfuse-auth`, `user-mgmt-service`, and `config-mgmt-service`. Its failure will trigger the [Kfuse User Access Service Availability](kfuse-user-access-service-availability.md) alert as well.

**Common Root Causes:**
- Pod OOMKilled — vector-based services can spike in memory under high throughput
- PVC full on `kfuse-configdb` — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md)
- Upstream dependency (Kafka, deep store) unavailable causing vector agents to crash
- Node pressure causing pod evictions — see [Node condition not Ready](node_status.md)
- Misconfigured credentials for cloud exporter or archival deep store

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Affected Components

### Alert: Kfuse-misc deployment pods are unavailable (Warning)
Fires when **1 or more** replicas are unavailable for **10 minutes**.

| Deployment | Role |
|------------|------|
| `hydration-service` | Orchestrates data replay/hydration for archival and backfill |
| `zapper` | Enforces data retention TTL — deletes expired data from Pinot and deep store |
| `az-service` | Availability zone metadata service |
| `kf-mcp` | Model Context Protocol integration service |
| `kfuse-archival-vector` | Vector agent for archiving logs/metrics/traces to long-term storage |
| `kfuse-enrichment-vector` | Vector agent for enriching telemetry with additional metadata |
| `kfuse-rum-vector` | Vector agent for Real User Monitoring data forwarding |
| `kfuse-audit-log-vector` | Vector agent for audit log forwarding |
| `kfuse-cloud-exporter` | Exports metrics to cloud monitoring services |

### Alert: Kfuse-misc statefulset pods are unavailable (Warning)
Fires when **1 or more** replicas are unavailable for **10 minutes**.

| StatefulSet | Role |
|-------------|------|
| `hydration-logs-parser` | Parses log data during hydration/replay operations |
| `kfuse-configdb` | PostgreSQL-backed configuration database — stores alerts, dashboards, users |

---

## Symptoms

### Alert Expressions

**Deployment (1+ unavailable):**
```promql
sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
  kubernetes_state_deployment_replicas_desired{
    kube_app_instance="kfuse",
    kube_deployment=~"hydration-service|zapper|az-service|kf-mcp|kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector|kfuse-cloud-exporter"
  }
) - sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
  kubernetes_state_deployment_replicas_available{
    kube_app_instance="kfuse",
    kube_deployment=~"hydration-service|zapper|az-service|kf-mcp|kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector|kfuse-cloud-exporter"
  }
) > 0
```

**StatefulSet (1+ unavailable):**
```promql
sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
  kubernetes_state_statefulset_replicas_desired{
    kube_app_instance="kfuse",
    kube_stateful_set=~"hydration-logs-parser|kfuse-configdb"
  }
) - sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
  kubernetes_state_statefulset_replicas_ready{
    kube_app_instance="kfuse",
    kube_stateful_set=~"hydration-logs-parser|kfuse-configdb"
  }
) > 0
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_state_deployment_replicas_desired - kubernetes_state_deployment_replicas_available` | `0` | `>= 1` |
| `kubernetes_state_statefulset_replicas_desired - kubernetes_state_statefulset_replicas_ready` | `0` | `>= 1` |

---

## Step 1: Identify the Affected Component

The alert description will identify the specific `kube_deployment` or `kube_stateful_set`. Check the alert details in the Kloudfuse UI or your notification channel.

List all misc-tier pods:

```bash
kubectl get pods -n kfuse | grep -E "hydration-service|zapper|az-service|kf-mcp|kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector|kfuse-cloud-exporter|hydration-logs-parser|kfuse-configdb"
```

---

## Step 2: Check Pod Status and Events

```bash
kubectl describe pod -n kfuse <POD_NAME>
```

Review the `Events` section for OOM kills, scheduling failures, or probe failures.

```bash
kubectl get events -n kfuse --sort-by='.lastTimestamp' | grep -E "Warning|Failed|OOM|Evict" | tail -20
```

---

## Step 3: Check Logs for Root Cause

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_deployment="<DEPLOYMENT_NAME>" and level=~"error|fatal"
```

For vector-based services (archival, enrichment, rum, audit-log):

```
kube_deployment=~"kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector" and ("error" or "failed" or "timeout")
```

For configdb:

```
kube_stateful_set="kfuse-configdb" and level=~"error|fatal"
```

For logs from a pod that has already restarted, filter by time range in the Kloudfuse Logs Search UI to cover the window before the restart:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod="<POD_NAME>" and level=~"error|fatal"
```

Common error patterns:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `no space left on device` | PVC full — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) |
| `connection refused` to Kafka | Kafka unavailable |
| `Access Denied` or `403` to S3/GCS/Azure | Cloud credentials expired or misconfigured |
| `FATAL: database` or `PGPASSWORD` error | configdb startup failure |
| `OOMKilled` | Memory limits too low — increase limits |

---

## Step 4: Diagnose Root Cause

### Case A: kfuse-configdb Unavailable (High Priority)

`kfuse-configdb` is a critical dependency. Its loss will cascade to `kfuse-auth`, `user-mgmt-service`, and `config-mgmt-service` within minutes.

Check configdb pod status:

```bash
kubectl get pods -n kfuse | grep kfuse-configdb
kubectl describe statefulset kfuse-configdb -n kfuse
```

Check configdb PVC usage — PostgreSQL will stop writing if the PVC is full:

```bash
kubectl get pvc -n kfuse | grep kfuse-configdb
```

If the PVC is near capacity, follow the [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) runbook immediately.

If the pod is crash-looping, check for database corruption or configuration issues:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_stateful_set="kfuse-configdb" and level=~"error|fatal"
```

### Case B: Vector Agent Unavailable (archival, enrichment, rum, audit-log)

Vector agents are lightweight pipelines for routing telemetry. They typically fail due to:
- Upstream Kafka topic connectivity issues
- Deep store (S3/GCS/Azure) credentials or connectivity issues
- Configuration errors (bad pipeline transform)

Check vector agent logs for pipeline or connectivity errors:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_deployment=~"kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector" and ("error" or "failed" or "timeout" or "Access Denied" or "connection refused")
```

For cloud credential issues, verify the associated IAM role or Kubernetes service account has the necessary permissions for the target storage bucket.

### Case C: zapper Unavailable

The `zapper` service enforces data retention. If it is down, old data will not be expired on schedule, which may cause Pinot PVCs to grow over time. This is not an immediate emergency but should be resolved.

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_deployment="zapper" and level=~"error|fatal"
```

### Case D: hydration-service or hydration-logs-parser Unavailable

These services handle data replay and backfill. If they are down, in-progress hydration jobs will stall. Check for errors:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_deployment="hydration-service" and level=~"error|fatal"
```

### Case E: kfuse-cloud-exporter Unavailable

The cloud exporter pushes metrics to external monitoring services. Check for authentication errors indicating cloud provider credential expiry:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_deployment="kfuse-cloud-exporter" and ("error" or "Auth" or "credentials" or "403" or "401")
```

---

## Step 5: Restart the Affected Component

**For a Deployment:**

```bash
kubectl rollout restart deployment/<DEPLOYMENT_NAME> -n kfuse
kubectl rollout status deployment/<DEPLOYMENT_NAME> -n kfuse
```

**For a StatefulSet:**

```bash
kubectl rollout restart statefulset/<STATEFULSET_NAME> -n kfuse
kubectl rollout status statefulset/<STATEFULSET_NAME> -n kfuse
```

**For a single pod:**

```bash
kubectl delete pod -n kfuse <POD_NAME>
```

**If kfuse-configdb is affected**, restart dependent services after configdb is healthy:

```bash
# After configdb is running
kubectl rollout restart deployment/kfuse-auth deployment/user-mgmt-service deployment/config-mgmt-service -n kfuse
```

---

## Step 6: Post-Recovery Verification

### Verify All Pods Are Running

```bash
kubectl get pods -n kfuse | grep -E "hydration-service|zapper|az-service|kf-mcp|kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector|kfuse-cloud-exporter|hydration-logs-parser|kfuse-configdb"
```

All pods should show `Running` with all containers ready.

### Verify configdb Is Accepting Connections

If `kfuse-configdb` was affected, verify that dependent services have reconnected by checking their logs:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_deployment=~"kfuse-auth|user-mgmt-service" and ("database" or "connection" or "error")
```

There should be no database connection errors after recovery.

### Verify via PromQL

```promql
# Should return 0 for all components
sum by (kube_deployment)(
  kubernetes_state_deployment_replicas_desired{
    kube_app_instance="kfuse",
    kube_deployment=~"hydration-service|zapper|az-service|kf-mcp|kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector|kfuse-cloud-exporter"
  }
) - sum by (kube_deployment)(
  kubernetes_state_deployment_replicas_available{
    kube_app_instance="kfuse",
    kube_deployment=~"hydration-service|zapper|az-service|kf-mcp|kfuse-archival-vector|kfuse-enrichment-vector|kfuse-rum-vector|kfuse-audit-log-vector|kfuse-cloud-exporter"
  }
)
```

---

## Prevention

### Monitor kfuse-configdb PVC

The configdb PVC is the most critical in this group. Alert at 80% capacity:

```promql
(
  max by (persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_used_bytes{kfuse="true", persistentvolumeclaim=~".*configdb.*"}
  ) * 100
  / max by (persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_capacity_bytes{kfuse="true", persistentvolumeclaim=~".*configdb.*"}
  )
) > 80
```

### Rotate Cloud Credentials Before Expiry

For `kfuse-cloud-exporter` and archival vector agents, set a calendar reminder to rotate cloud provider credentials before their expiry date to prevent sudden credential failures.

---

## Related Runbooks

- [Kfuse User Access Service Availability](kfuse-user-access-service-availability.md) — User-facing services that depend on kfuse-configdb
- [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) — PVC full on kfuse-configdb
- [Node condition not Ready](node_status.md) — Node-level failures causing pod evictions
- [Kfuse Ingest Service Availability](kfuse-ingest-service-availability.md) — Upstream ingest dependencies for vector agents
