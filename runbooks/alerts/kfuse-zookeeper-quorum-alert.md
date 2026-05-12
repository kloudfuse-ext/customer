# Kfuse Zookeeper Quorum Alert

## Table of Contents

- [Summary](#summary)
- [Symptoms](#symptoms)
- [Step 1: Check ZooKeeper Pod Status](#step-1-check-zookeeper-pod-status)
- [Step 2: Assess Quorum State](#step-2-assess-quorum-state)
- [Step 3: Check ZooKeeper Logs](#step-3-check-zookeeper-logs)
- [Step 4: Diagnose Root Cause](#step-4-diagnose-root-cause)
- [Step 5: Restore ZooKeeper Quorum](#step-5-restore-zookeeper-quorum)
- [Step 6: Verify Pinot Health After Recovery](#step-6-verify-pinot-health-after-recovery)
- [Step 7: Post-Recovery Verification](#step-7-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

ZooKeeper provides distributed coordination for the Apache Pinot cluster. A standard Pinot deployment uses a 3-node ZooKeeper ensemble, which requires at least 2 nodes (a quorum majority) to be running to elect a leader and serve read and write requests.

This alert fires when **1 or more** ZooKeeper pods are unavailable for **10 minutes**. With 3 replicas, losing even 1 node means the remaining 2 nodes are at risk — any additional failure will cause a full quorum loss, at which point Pinot cannot make metadata changes, assign segments, or register new servers.

**Impact:**
- **1 ZooKeeper pod unavailable (alert fires):** ZooKeeper quorum is maintained (2 of 3 still running) but there is zero fault tolerance. Pinot continues to function for reads and writes, but any additional ZooKeeper failure will cause a full outage.
- **2 ZooKeeper pods unavailable (quorum lost):** Pinot cannot elect a controller leader, cannot assign new segments, and realtime ingestion will stall. Existing offline query results may continue temporarily from cached data on Pinot servers.
- **All ZooKeeper pods unavailable:** Pinot cluster is fully unavailable.

**Common Root Causes:**
- Node pressure causing ZooKeeper pod eviction — see [Node condition not Ready](node_status.md)
- PVC full — ZooKeeper writes transaction logs to disk; a full PVC causes it to crash — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md)
- JVM OOM — ZooKeeper heap exhausted
- Split-brain from network partition — pods cannot reach each other
- Recent rolling restart that left a pod stuck

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Symptoms

### Alert Expression

```promql
sum by (org_id, kube_cluster_name, kube_namespace)(
  kubernetes_state_statefulset_replicas_desired{
    kube_app_instance="kfuse",
    kube_stateful_set="pinot-zookeeper"
  }
) - sum by (org_id, kube_cluster_name, kube_namespace)(
  kubernetes_state_statefulset_replicas_ready{
    kube_app_instance="kfuse",
    kube_stateful_set="pinot-zookeeper"
  }
) > 0
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_state_statefulset_replicas_desired - kubernetes_state_statefulset_replicas_ready` (pinot-zookeeper) | `0` | `>= 1` |
| `pinot_controller_percentSegmentsAvailable_Value` | `100` | `< 100` (may drop after extended ZK outage) |

### Downstream Symptoms

- Pinot controller logs show `ZooKeeper connection lost` or `session expired`
- New realtime segments are not being created
- `pinot_controller_realtimeTableCount` stops changing
- The [Pinot Segments Unavailable](pinot-segments-unavailable.md) alert may fire if outage is prolonged

---

## Step 1: Check ZooKeeper Pod Status

```bash
kubectl get pods -n kfuse | grep pinot-zookeeper
```

Expected healthy output:

```
pinot-zookeeper-0     1/1     Running   0     2d
pinot-zookeeper-1     1/1     Running   0     2d
pinot-zookeeper-2     1/1     Running   0     2d
```

Identify which pods are not `Running` or have recent restarts (`RESTARTS > 0` is worth investigating).

Describe each unhealthy pod:

```bash
kubectl describe pod -n kfuse <ZOOKEEPER_POD_NAME>
```

Check the `Events` section for:
- OOM kills
- PVC mount failures
- Node assignment and eviction reasons

---

## Step 2: Assess Quorum State

Determine how many ZooKeeper nodes are currently healthy:

```bash
kubectl get pods -n kfuse -l app=pinot-zookeeper --no-headers | grep Running | wc -l
```

| Running Nodes | Quorum State | Urgency |
|---------------|-------------|---------|
| 3 | Healthy (alert should not be firing) | — |
| 2 | Quorum maintained — zero fault tolerance | **High: restore immediately** |
| 1 | Quorum lost — Pinot is degraded or down | **Critical: restore now** |
| 0 | Cluster down | **Emergency** |

If quorum is lost (fewer than 2 nodes running), proceed directly to [Step 5](#step-5-restore-zookeeper-quorum).

---

## Step 3: Check ZooKeeper Logs

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="pinot-zookeeper" and level=~"warn|error"
```

Or for specific failure modes:

```
kube_service="pinot-zookeeper" and ("quorum" or "leader" or "election" or "disk" or "IOException" or "OutOfMemory")
```

For logs from pods that have already restarted, filter by time range to cover the window before the restart:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="pinot-zookeeper" and level=~"error|warn"
```

Common log patterns:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `OutOfMemoryError` | JVM heap too small — increase memory |
| `IOException: No space left on device` | PVC full — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) |
| `LOOKING` state on multiple nodes | Leader election in progress (may be transient) |
| `Connection to ... closed` | Network partition between ZooKeeper nodes |
| `Session expired` | ZooKeeper session dropped — Pinot reconnecting |

---

## Step 4: Diagnose Root Cause

### Case A: PVC Full

ZooKeeper writes transaction logs and snapshots continuously. If the PVC fills, ZooKeeper cannot write and will crash.

Check PVC usage:

```bash
kubectl get pvc -n kfuse | grep zookeeper
```

If the PVC is at or near capacity, follow the [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) runbook before restarting ZooKeeper. Starting ZooKeeper on a full disk will just cause it to crash again immediately.

ZooKeeper transaction logs can also be cleaned up manually to free space:

```bash
kubectl exec -n kfuse pinot-zookeeper-0 -- \
  find /bitnami/zookeeper/data/version-2 -name "log.*" -mtime +1 | sort | head -n -3
```

> **Warning:** Only remove old transaction log files. Keep the most recent 3 log files and all snapshots. Confirm with your team before deleting ZooKeeper data.

### Case B: Pod Eviction Due to Node Pressure

If ZooKeeper pods were evicted from nodes due to memory or disk pressure, the node issue must be resolved first:

```bash
kubectl get events -n kfuse --sort-by='.lastTimestamp' | grep -E "Evict|zookeeper"
```

See [Node condition not Ready](node_status.md) to resolve node pressure before restarting ZooKeeper.

### Case C: OOMKilled

If ZooKeeper is being OOMKilled, the JVM heap needs to be increased. Confirm by checking ZooKeeper logs for the OOM error:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="pinot-zookeeper" and "OutOfMemoryError"
```

Increase the heap size by updating `pinot.zookeeper.heapSize` in `values.yaml`. The value is in MB (default is `4096`):

```yaml
# charts/kfuse/values.yaml — pinot.zookeeper section (line ~1598)
pinot:
  zookeeper:
    heapSize: 8192   # increase from default 4096
```

Apply the change with a `helm upgrade` and allow the ZooKeeper pods to restart with the new heap allocation.

### Case D: Network Partition (Split-Brain)

If ZooKeeper pods are running but cannot reach each other, you may see all nodes in `LOOKING` state:

```bash
for i in 0 1 2; do
  echo "ZooKeeper $i:"
  kubectl exec -n kfuse pinot-zookeeper-$i -- \
    zkServer.sh status 2>/dev/null || echo "zkServer.sh not available"
done
```

Verify that pods can reach each other via the headless service:

```bash
kubectl exec -n kfuse pinot-zookeeper-0 -- \
  nc -zv pinot-zookeeper-1.pinot-zookeeper-headless.kfuse.svc.cluster.local 2888
```

A network partition typically requires investigating the CNI/networking layer — see [Node condition not Ready](node_status.md) for NetworkUnavailable cases.

---

## Step 5: Restore ZooKeeper Quorum

### Option A: Restart the Failed Pod(s)

If the root cause (PVC, OOM, node) has been resolved, restart the failed ZooKeeper pod(s):

```bash
# Restart a specific pod
kubectl delete pod -n kfuse pinot-zookeeper-<N>

# Wait for it to become ready
kubectl wait --for=condition=Ready pod/pinot-zookeeper-<N> -n kfuse --timeout=300s
```

Monitor the restart in another terminal:

```bash
kubectl get pods -n kfuse -w | grep zookeeper
```

ZooKeeper will re-join the ensemble automatically after starting.

### Option B: Full Ensemble Restart (if all nodes are down)

If all ZooKeeper nodes are down and need to be restarted, bring them up one at a time to allow leader election:

```bash
kubectl delete pod -n kfuse pinot-zookeeper-0
kubectl wait --for=condition=Ready pod/pinot-zookeeper-0 -n kfuse --timeout=300s

kubectl delete pod -n kfuse pinot-zookeeper-1
kubectl wait --for=condition=Ready pod/pinot-zookeeper-1 -n kfuse --timeout=300s

kubectl delete pod -n kfuse pinot-zookeeper-2
kubectl wait --for=condition=Ready pod/pinot-zookeeper-2 -n kfuse --timeout=300s
```

> **Note:** Starting all ZooKeeper nodes at the same time may delay leader election. Starting sequentially is safer.

### Verify Quorum After Restart

```bash
kubectl get pods -n kfuse | grep pinot-zookeeper
```

All 3 pods should be `Running 1/1`.

Check ZooKeeper logs for a successful leader election message:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="pinot-zookeeper" and ("LEADER" or "FOLLOWER" or "quorum" or "election")
```

---

## Step 6: Verify Pinot Health After Recovery

After ZooKeeper is restored, Pinot components will automatically reconnect to ZooKeeper and resume normal operation. However, this may take a few minutes.

Check that the Pinot controller reconnected:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="pinot-controller" and ("ZooKeeper" or "connected" or "leader" or "session")
```

Check that Pinot brokers are registered:

```bash
CONTROLLER_POD=$(kubectl get pods -n kfuse -l app=pinot-controller -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/brokers/tenants/DefaultTenant"
```

If the output lists broker instances, Pinot coordination is restored.

If Pinot segments became unavailable during the ZooKeeper outage, follow the [Pinot Segments Unavailable](pinot-segments-unavailable.md) runbook.

---

## Step 7: Post-Recovery Verification

### Verify ZooKeeper Replicas

```promql
# Should return 0
sum(kubernetes_state_statefulset_replicas_desired{kube_app_instance="kfuse", kube_stateful_set="pinot-zookeeper"})
- sum(kubernetes_state_statefulset_replicas_ready{kube_app_instance="kfuse", kube_stateful_set="pinot-zookeeper"})
```

### Verify Pinot Segment Availability

```promql
avg by (table)(
  pinot_controller_percentSegmentsAvailable_Value{
    kfuse="true",
    kube_service="pinot-controller",
    table=~"kf_logs|kf_metrics|kf_metrics_rollup"
  }
)
```

Should return `100` for all tables.

### Verify Data Is Flowing

In the Kloudfuse UI, confirm that:
1. New logs are visible in **Logs** → **Live Tail**
2. New metrics are appearing in **Metrics** → **Explorer**
3. No `Pinot Segments Unavailable` alert is firing

---

## Prevention

### Monitor ZooKeeper PVC Usage

ZooKeeper PVCs should be monitored aggressively. Alert at 70% to give ample warning:

```promql
(
  max by (persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_used_bytes{kfuse="true", persistentvolumeclaim=~".*zookeeper.*"}
  ) * 100
  / max by (persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_capacity_bytes{kfuse="true", persistentvolumeclaim=~".*zookeeper.*"}
  )
) > 70
```

### Enable ZooKeeper Autopurge

Configure ZooKeeper to automatically purge old snapshots and transaction logs to prevent disk accumulation. In `values.yaml`:

```yaml
zookeeper:
  configuration: |
    autopurge.snapRetainCount=3
    autopurge.purgeInterval=1
```

This retains only the last 3 snapshots and purges old logs hourly.

### Spread ZooKeeper Pods Across Nodes

Use pod anti-affinity to ensure ZooKeeper pods are on different nodes, so a single node failure does not take down two ZooKeeper pods:

```yaml
zookeeper:
  affinity:
    podAntiAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:
        - labelSelector:
            matchLabels:
              app: pinot-zookeeper
          topologyKey: kubernetes.io/hostname
```

---

## Related Runbooks

- [Pinot Segments Unavailable](pinot-segments-unavailable.md) — Downstream impact of ZooKeeper loss on Pinot
- [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) — ZooKeeper PVC full
- [Node condition not Ready](node_status.md) — Node-level failures causing ZooKeeper eviction
- [Kfuse Query Service Availability](kfuse-query-service-availability.md) — Query-tier impact of ZooKeeper loss
