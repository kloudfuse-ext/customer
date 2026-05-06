# Kfuse Query Service Availability

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

The query service availability alerts fire when multiple pods in the Kloudfuse query tier become unavailable. These services are responsible for executing user queries across logs, metrics, traces, events, and RUM data. The scalable thresholds (3+ pods unavailable) are used because these services are horizontally scaled — a few unavailable replicas degrade performance rather than causing a full outage.

**Impact:** Depending on the affected component:
- **query-service:** Metrics and general queries fail or time out
- **trace-query-service:** APM and distributed trace queries are unavailable
- **events-query-service:** Events queries are unavailable
- **rum-query-service:** Real User Monitoring queries are unavailable
- **logs-query-service:** Log search and tail queries are unavailable
- **pinot-controller:** Pinot cluster management fails; segment assignments cannot be rebalanced; segment availability degrades over time
- **pinot-broker:** Query routing to Pinot servers fails; all Pinot-backed queries return errors
- **pinot-server-realtime / pinot-server-offline:** Queries return partial data; realtime ingestion may also be impacted

**Common Root Causes:**
- Node pressure causing pod eviction — see [Node condition not Ready](node_status.md)
- PVC full on Pinot servers — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md)
- Pinot servers OOMKilled due to large query workloads
- ZooKeeper quorum loss disrupting Pinot state — see [Kfuse Zookeeper Quorum Alert](kfuse-zookeeper-quorum-alert.md)
- Recent Helm upgrade causing rolling restart with insufficient surge capacity
- Query service crash due to upstream dependency (Pinot broker) being unavailable

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Affected Components

### Alert: Kfuse-query deployment pods are unavailable (Critical)
Fires when **3 or more** replicas are unavailable (or **4+** if desired >= 11) for **10 minutes**.

| Deployment | Role |
|------------|------|
| `query-service` | Executes metrics and general queries against Pinot |
| `trace-query-service` | Executes APM and distributed trace queries |
| `events-query-service` | Executes events queries |
| `rum-query-service` | Executes Real User Monitoring queries |

### Alert: Kfuse-query scalable statefulset pods are unavailable (Critical)
Fires when **3 or more** replicas are unavailable (or **4+** if desired >= 11) for **10 minutes**.

| StatefulSet | Role |
|-------------|------|
| `logs-query-service` | Executes log search and streaming queries |
| `pinot-controller` | Manages Pinot cluster: segment assignments, table configs, broker registration |
| `pinot-broker` | Routes queries to the correct Pinot servers; aggregates results |
| `pinot-server-realtime` | Serves realtime (in-flight) segments; participates in REALTIME table queries |
| `pinot-server-offline` | Serves offline (committed) segments; participates in OFFLINE table queries |
| `pinot-minion` | Runs background tasks: compaction, purge, segment generation |

---

## Symptoms

### Alert Expressions

**Scalable deployment (3+ unavailable):**
```promql
(
  sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
    kubernetes_state_deployment_replicas_desired{
      kube_app_instance="kfuse",
      kube_deployment=~"query-service|trace-query-service|events-query-service|rum-query-service"
    }
  ) - sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
    kubernetes_state_deployment_replicas_available{
      kube_app_instance="kfuse",
      kube_deployment=~"query-service|trace-query-service|events-query-service|rum-query-service"
    }
  )
) >= 3
```

**Scalable statefulset (3+ unavailable):**
```promql
(
  sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
    kubernetes_state_statefulset_replicas_desired{
      kube_app_instance="kfuse",
      kube_service="<PINOT-SERVICE>"
    }
  ) - sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
    kubernetes_state_statefulset_replicas_ready{
      kube_app_instance="kfuse",
      kube_service="<PINOT-SERVICE>"
    }
  )
) >= 3
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_state_deployment_replicas_desired - kubernetes_state_deployment_replicas_available` | `0` | `>= 3` |
| `kubernetes_state_statefulset_replicas_desired - kubernetes_state_statefulset_replicas_ready` | `0` | `>= 3` |
| `pinot_controller_percentSegmentsAvailable_Value` | `100` | `< 90` |

### Dashboard

Navigate to: Kloudfuse UI → **Dashboards** → **CP Dashboards** → **pinot** for Pinot cluster health.

For query service health: **Dashboards** → **CP Dashboards** → **kfuse-cp**

---

## Step 1: Identify the Affected Component

The alert description will identify the specific `kube_deployment` or `kube_stateful_set`. Check the alert details in Kloudfuse UI or your notification channel.

List all pods for the affected component:

```bash
# For a deployment
kubectl get pods -n kfuse | grep <DEPLOYMENT_NAME>

# For a statefulset
kubectl get pods -n kfuse | grep <STATEFULSET_NAME>

# Get an overview of all query-tier pods
kubectl get pods -n kfuse | grep -E "query-service|trace-query|events-query|rum-query|logs-query|pinot"
```

---

## Step 2: Check Pod Status and Events

Describe the affected pod:

```bash
kubectl describe pod -n kfuse <POD_NAME>
```

Check the `Events` section for scheduling failures, OOM kills, or readiness probe failures.

Check recent namespace-level events:

```bash
kubectl get events -n kfuse --sort-by='.lastTimestamp' | grep -E "Warning|Failed|OOM|Evict" | tail -30
```

For Pinot pods, verify that ZooKeeper is healthy — Pinot depends on ZooKeeper for all coordination:

```bash
kubectl get pods -n kfuse | grep pinot-zookeeper
```

If ZooKeeper pods are unavailable, follow the [Kfuse Zookeeper Quorum Alert](kfuse-zookeeper-quorum-alert.md) runbook first.

---

## Step 3: Check Logs for Root Cause

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

For query service deployments:

```
kube_service="<QUERY-SERVICE>" and level=~"error|fatal"
```

For Pinot components:

```
kube_service="<PINOT-SERVICE>" and level=~"warn|error"
```

Common error patterns:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `OutOfMemoryError` | JVM heap exhausted — increase memory limits or JVM heap size |
| `ZooKeeper connection lost` | ZooKeeper instability — check ZooKeeper pods |
| `Failed to connect to broker` | Pinot broker unavailable |
| `no space left on device` | PVC full — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) |
| `Failed to download segment` | Deep store connectivity issue |
| `QueryException: No server found` | Pinot servers not serving segments |

For logs from a pod that has already restarted, filter by time range in the Kloudfuse Logs Search UI to cover the window before the restart:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod="<POD_NAME>" and level=~"error|fatal"
```

---

## Step 4: Diagnose Root Cause

### Case A: Pinot Server Unavailable (realtime or offline)

Pinot servers hold query data. If servers are down, segment availability drops and queries return partial data.

Check Pinot server pod status:

```bash
kubectl get pods -n kfuse | grep pinot-server
```

If servers are crashing, check for OOM or disk pressure events in the Pinot server logs:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="<PINOT-SERVICE>" and level=~"error|warn"
```

Look for these patterns:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `OutOfMemoryError` | JVM heap exhausted — increase `jvmMemory` in values.yaml |
| `no space left on device` | PVC full — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) |
| `Failed to load segment` | Segment download or disk issue |
| `Timed out waiting` | Slow deep store reads during segment load |

If PVCs are near capacity, follow the [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) runbook.

For segment-level issues that have already occurred, follow the [Pinot Segments Unavailable](pinot-segments-unavailable.md) runbook.

### Case B: Pinot Broker Unavailable

The Pinot broker routes queries to servers. Without a broker, all Pinot queries fail immediately.

Check broker pod status:

```bash
kubectl get pods -n kfuse | grep pinot-broker
```

Check broker logs for startup or ZooKeeper errors:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

To find queries that are timing out or failing at the broker:

```
kube_service="pinot-broker" and ("QueryException" or "timeoutMs" or "No server found" or "failed to route")
```

To identify slow or expensive queries being received by the broker:

```
kube_service="pinot-broker" and ("timeUsedMs" or "numDocsScanned" or "numSegmentsQueried") and level=~"warn|error"
```

If the broker is starting slowly (e.g., re-reading table configs from ZooKeeper), wait up to 5 minutes after pod startup for readiness.

### Case C: Pinot Controller Unavailable

The controller manages the overall Pinot cluster. Loss of the controller does not immediately affect read queries (servers and brokers can serve existing segments), but segment rebalancing, new segment creation, and Pinot operational tasks will fail.

Check controller logs for ZooKeeper connection errors:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="pinot-controller" and ("ZooKeeper" or "Leader" or "session expired")
```

Check for segment assignment failures or rebalance errors:

```
kube_service="pinot-controller" and ("segment" or "rebalance" or "assign" or "ERROR") and level=~"error|warn"
```

### Case D: Query Service Deployment Pods Unavailable

Query services (`query-service`, `trace-query-service`, etc.) are stateless. They typically fail due to:
- Pinot broker being unavailable (upstream dependency)
- Application crash after a code deployment
- Memory limits exceeded under heavy query load
- A single expensive query consuming all resources

**Check for application errors and crashes:**

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="<QUERY-SERVICE>" and level=~"error|fatal"
```

**Check for slow or timed-out queries causing the service to back up:**

```
kube_service="<QUERY-SERVICE>" and ("timeout" or "deadline exceeded" or "context canceled" or "upstream request timeout")
```

**Check for Pinot broker connectivity errors from the query service:**

```
kube_service="query-service" and ("connection refused" or "broker" or "no healthy upstream" or "503")
```

**Identify queries that returned errors to users:**

```
kube_service="<QUERY-SERVICE>" and ("QueryError" or "failed" or "error") and level="error"
```

**Check for memory pressure in the query service:**

```
kube_service="<QUERY-SERVICE>" and ("OOM" or "OutOfMemory" or "memory" or "heap") and level=~"error|warn"
```

Check if a recent deployment is the cause:

```bash
kubectl rollout history deployment/<DEPLOYMENT_NAME> -n kfuse
kubectl rollout status deployment/<DEPLOYMENT_NAME> -n kfuse
```

If a bad deployment is causing crashes, roll back:

```bash
kubectl rollout undo deployment/<DEPLOYMENT_NAME> -n kfuse
```

### Case E: Logs Query Service Unavailable

The `logs-query-service` is a StatefulSet. It executes FuseQL log search queries backed by Pinot and is memory-intensive under high query load.

**Check for errors in the logs query service:**

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="logs-query-service" and level=~"error|fatal"
```

**Check for slow or timed-out log search queries:**

```
kube_service="logs-query-service" and ("timeout" or "deadline exceeded" or "context canceled" or "slow query")
```

**Check for Pinot connectivity issues from the logs query service:**

```
kube_service="logs-query-service" and ("pinot" or "broker" or "connection refused" or "failed") and level=~"error|warn"
```

**Check for memory pressure:**

```
kube_service="logs-query-service" and ("OOM" or "OutOfMemory" or "heap") and level=~"error|warn"
```

Check PVC status for the logs-query-service StatefulSet:

```bash
kubectl get pvc -n kfuse | grep logs-query-service
```

---

## Step 5: Restart the Affected Component

After resolving the underlying cause, restart the component:

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

**For a specific pod:**

```bash
kubectl delete pod -n kfuse <POD_NAME>
```

**Restart order for Pinot (if multiple components are down):**

Restart in this order to minimize coordination errors:
1. `pinot-zookeeper` (if affected — see [Kfuse Zookeeper Quorum Alert](kfuse-zookeeper-quorum-alert.md))
2. `pinot-controller`
3. `pinot-broker`
4. `pinot-server-realtime`
5. `pinot-server-offline`
6. `pinot-minion`

---

## Step 6: Post-Recovery Verification

### Verify All Pods Are Running

```bash
kubectl get pods -n kfuse | grep -E "query-service|trace-query|events-query|rum-query|logs-query|pinot"
```

All pods should show `Running` with all containers ready.

### Verify Pinot Segment Availability

```bash
CONTROLLER_POD=$(kubectl get pods -n kfuse -l app=pinot-controller -o jsonpath='{.items[0].metadata.name}')

# Check percent segments available for key tables
kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/kf_logs_REALTIME/segments/metadata" | \
  python3 -c "import sys,json; data=json.load(sys.stdin); print(data)"
```

Or use PromQL in Kloudfuse:

```promql
pinot_controller_percentSegmentsAvailable_Value{
  kfuse="true",
  kube_service="pinot-controller",
  table=~"kf_logs|kf_metrics|kf_metrics_rollup"
}
```

Should return `100` for all tables.

### Verify Queries Are Returning Data

In the Kloudfuse UI, test a log search and a metrics query to confirm end-to-end query functionality is restored.

### Verify Replica Counts

```promql
# Should return 0
sum by (kube_stateful_set)(
  kubernetes_state_statefulset_replicas_desired{
    kube_app_instance="kfuse",
    kube_service="<PINOT-SERVICE>"
  }
) - sum by (kube_stateful_set)(
  kubernetes_state_statefulset_replicas_ready{
    kube_app_instance="kfuse",
    kube_service="<PINOT-SERVICE>"
  }
)
```

---

## Prevention

### Size Pinot Server Memory Appropriately

Large query workloads cause OOM on Pinot servers. Tune the JVM heap size in `values.yaml` under the `pinot.server` section. The `jvmMemory` field controls the amount of memory for each server type:

```yaml
# charts/kfuse/values.yaml — pinot.server
pinot:
  server:
    realtime:
      jvmMemory: "8G"
    offline:
      jvmMemory: "4G"
```

### Monitor Pinot Segment Availability

```promql
avg by (table)(
  pinot_controller_percentSegmentsAvailable_Value{
    kfuse="true",
    table=~"kf_logs|kf_metrics|kf_metrics_rollup"
  }
) < 95
```

### Monitor PVC Capacity for Pinot

```promql
(
  max by (persistentvolumeclaim)(kubernetes_kubelet_volume_stats_used_bytes{kfuse="true"})
  * 100
  / max by (persistentvolumeclaim)(kubernetes_kubelet_volume_stats_capacity_bytes{kfuse="true"})
) > 80
```

---

## Related Runbooks

- [Pinot Segments Unavailable](pinot-segments-unavailable.md) — Segment-level availability issues
- [Pinot Segments in Error State](pinot-segments-in-error-state.md) — Hard segment errors
- [Kfuse Zookeeper Quorum Alert](kfuse-zookeeper-quorum-alert.md) — ZooKeeper quorum loss
- [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) — PVC full on Pinot or Kafka
- [Node condition not Ready](node_status.md) — Node-level failures causing evictions
- [Kfuse Ingest Service Availability](kfuse-ingest-service-availability.md) — Ingest-side failures
