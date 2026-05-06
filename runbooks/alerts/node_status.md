# Kubernetes Node Status

## Summary

A node, when healthy, is in a *Ready* condition and can accept Pods. If a node is under stress it can be unable to run new pods, and will no longer be in a *Ready* condition.

A node may also be unschedulable, meaning Kubernetes cannot schedule any new pods to run on that node.

**Impact:** Workloads cannot be scheduled on affected nodes. If enough nodes are unhealthy, pending pods will accumulate and cluster capacity will degrade. Existing pods on affected nodes may be evicted depending on the condition severity and node controller behavior.

**Common Root Causes:**
- Node is out of disk space (DiskPressure)
- Node is out of memory (MemoryPressure)
- Too many processes running on the node (PIDPressure)
- Network misconfiguration on the node (NetworkUnavailable)
- Node has lost connectivity with the control plane — kubelet not heartbeating (Ready=Unknown)
- Node crashed or was terminated by the cloud provider (Ready=False)
- Node was manually cordoned for maintenance (Unschedulable)

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Node Conditions

You can refer to the [official documentation](https://kubernetes.io/docs/reference/node/node-status/#condition). Listed below are the default conditions, though more may be supported by the cluster vendor.

| Condition | Description |
|-----------|-------------|
| Ready | **True** if the node is healthy and ready to accept pods<br>**False** if the node is not healthy and is not accepting pods<br>**Unknown** if the node controller has not heard from the node in the last `node-monitor-grace-period` (default is 50 seconds) |
| DiskPressure | **True** if pressure exists on the disk size — that is, if the disk capacity is low; otherwise **False** |
| MemoryPressure | **True** if pressure exists on the node memory — that is, if the node memory is low; otherwise **False** |
| PIDPressure | **True** if pressure exists on the processes — that is, if there are too many processes on the node; otherwise **False** |
| NetworkUnavailable | **True** if the network for the node is not correctly configured; otherwise **False** |

---

## Symptoms

### Alert Expression

```promql
(
    sum by (org_id, kube_cluster_name, kf_node, condition, status)(
      kubernetes_state_node_by_condition{
        kfuse="true",
        condition="Ready",
        status=~"false|unknown",
        kf_node!=""
      }
    )
  )
  or
  (
    sum by (org_id, kube_cluster_name, kf_node, condition, status)(
      kubernetes_state_node_by_condition{
        kfuse="true",
        condition=~"MemoryPressure|DiskPressure|PIDPressure|NetworkUnavailable",
        status="true",
        kf_node!=""
      }
    )
  )
  or
  (
    sum by (org_id, kube_cluster_name, node, status)(
      kubernetes_state_node_status{
        kfuse="true",
        status="unschedulable"
      }
    )
  )
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_state_node_by_condition{condition="Ready"}` | `status="true"` | `status="false"` or `status="unknown"` |
| `kubernetes_state_node_by_condition{condition="DiskPressure"}` | `status="false"` | `status="true"` |
| `kubernetes_state_node_by_condition{condition="MemoryPressure"}` | `status="false"` | `status="true"` |
| `kubernetes_state_node_by_condition{condition="PIDPressure"}` | `status="false"` | `status="true"` |
| `kubernetes_state_node_by_condition{condition="NetworkUnavailable"}` | `status="false"` | `status="true"` |
| `kubernetes_state_node_status{status="unschedulable"}` | `0` | `> 0` (node cordoned) |

---

## Step 1: Identify Affected Nodes

Get an overview of all node statuses:

```bash
kubectl get nodes
```

Look for nodes showing `NotReady`, `SchedulingDisabled`, or pressure taints in the `STATUS` column:

```
NAME                                       STATUS                     ROLES    AGE
gke-prod-pool-1-abc123                     Ready                      <none>   10d
gke-prod-pool-1-def456                     NotReady                   <none>   10d
gke-prod-pool-1-ghi789                     Ready,SchedulingDisabled   <none>   10d
```

For the specific node from the alert, describe it to view all conditions:

```bash
kubectl describe node <NODE_NAME>
```

Check the `Conditions` section in the output:

```
Conditions:
  Type                 Status  LastHeartbeatTime               Reason                       Message
  ----                 ------  -----------------               ------                       -------
  MemoryPressure       False   Wed, 14 May 2025 16:15:49 ...   KubeletHasSufficientMemory   kubelet has sufficient memory available
  DiskPressure         False   Wed, 14 May 2025 16:15:49 ...   KubeletHasNoDiskPressure     kubelet has no disk pressure
  PIDPressure          False   Wed, 14 May 2025 16:15:49 ...   KubeletHasSufficientPID      kubelet has sufficient PID available
  Ready                False   Wed, 14 May 2025 16:15:49 ...   KubeletNotReady              container runtime is down
```

Also check the `Events` section at the bottom of the describe output for recent warnings.

---

## Step 2: Check Node Resource Usage

SSH into the node or use a debug pod to inspect resource usage:

```bash
# Launch a debug pod on the affected node
kubectl debug node/<NODE_NAME> -it --image=ubuntu -- bash
```

Inside the debug pod:

```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check process count
ps aux | wc -l

# Check overall resource pressure
top
```

Alternatively, check resource metrics via the metrics server:

```bash
kubectl top node <NODE_NAME>
```

---

## Step 3: Diagnose Root Cause by Condition

### Case A: Ready=False or Ready=Unknown

**Ready=False** — the kubelet is running but reporting the node is not healthy (e.g., container runtime is down).

**Ready=Unknown** — the node controller has stopped receiving heartbeats from the kubelet. The node may be unreachable.

Check kubelet status by searching Kloudfuse logs.

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kf_node="<NODE_NAME>" and ("kubelet" or "container runtime" or "not ready")
```

Or check directly if you have SSH access to the node:

```bash
# Check kubelet service
systemctl status kubelet

# View kubelet logs
journalctl -u kubelet -n 100 --no-pager
```

Common causes and resolutions:

| Symptom in Logs | Likely Cause | Resolution |
|----------------|--------------|------------|
| `container runtime is down` | Docker/containerd crashed | Restart the container runtime on the node |
| `failed to connect to apiserver` | Network or API server issue | Check VPN/network connectivity to control plane |
| `node not found` | Node was deleted from cluster | Node may need to be re-registered |
| No heartbeats, node unreachable | Node crashed or was terminated | Check cloud provider console; replace node if terminated |

**Resolution for Ready=Unknown (node unreachable):** If the node is truly gone (e.g., cloud provider terminated it), remove it from the cluster:

```bash
kubectl delete node <NODE_NAME>
```

The node group autoscaler will provision a replacement if configured.

### Case B: DiskPressure

The kubelet is reporting that available disk space is critically low. This can cause pod evictions.

Refer to [this article](https://www.groundcover.com/blog/kubernetes-disk-pressure) for a detailed walkthrough of DiskPressure and how to resolve it.

Check disk usage on the node:

```bash
kubectl debug node/<NODE_NAME> -it --image=ubuntu -- df -h
```

Common causes:

| Cause | Resolution |
|-------|------------|
| Container image accumulation | Run `crictl rmi --prune` or `docker system prune` on the node |
| Large log files in `/var/log` | Rotate or truncate logs; ensure log rotation is configured |
| Pod writing excessive data to ephemeral storage | Identify the pod with `kubectl get pods --field-selector=spec.nodeName=<NODE_NAME>` and set `ephemeral-storage` limits |
| Node disk is undersized | Expand the node's disk volume via cloud provider console, or replace with a larger instance type |

### Case C: MemoryPressure

The kubelet is reporting that available memory is critically low. The kubelet will begin evicting pods ordered by QoS class (BestEffort first, then Burstable).

Check which pods are consuming the most memory on the node:

```bash
kubectl top pods --all-namespaces --sort-by=memory | grep <NODE_NAME>
```

Or check Kloudfuse for OOM events:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kf_node="<NODE_NAME>" and ("OOMKilled" or "out of memory" or "memory pressure")
```

Common causes:

| Cause | Resolution |
|-------|------------|
| Pod with no memory limits consuming all node memory | Set `resources.limits.memory` on the offending pod/deployment |
| Memory leak in an application | Restart the pod; investigate and fix the leak |
| Node memory is undersized for workload | Move workloads to a larger node type or add nodes to the pool |

### Case D: PIDPressure

The node is running too many processes. This is less common but can occur when applications fork excessively or init systems misbehave.

Identify the pod responsible:

```bash
# On the node via debug pod
ps aux | sort -rn -k 4 | head -20
```

**Resolution:** Identify and restart the offending pod. Set `spec.containers[].resources` PID limits if supported by your kernel version, or increase the node's PID limit via kubelet configuration (`--pod-max-pids`).

### Case E: NetworkUnavailable

The node's network plugin has reported that networking is not correctly configured. This typically indicates a CNI (Container Network Interface) plugin issue.

Check CNI pod health:

```bash
# Common CNI pods — adjust label selectors for your CNI (Calico, Flannel, Cilium, etc.)
kubectl get pods -n kube-system | grep -E "calico|flannel|cilium|weave"
```

Check CNI logs in Kloudfuse:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_namespace="kube-system" and kf_node="<NODE_NAME>" and ("network" or "CNI" or "route")
```

**Resolution:** Restart the CNI pod on the affected node, or drain and restart the node to allow the CNI to re-initialize:

```bash
kubectl drain <NODE_NAME> --ignore-daemonsets --delete-emptydir-data
# Then restart the node via cloud provider console or node group rolling update
kubectl uncordon <NODE_NAME>
```

---

## Step 4: Check Node Events

Review recent events for the node to identify patterns:

```bash
kubectl get events --field-selector involvedObject.name=<NODE_NAME> --sort-by='.lastTimestamp'
```

Look for recurring warnings such as evictions, OOM kills, or kubelet errors.

---

## Step 5: Unschedulable Nodes

If a node has been cordoned, Kubernetes will mark it unschedulable. A cordoned node continues to host its existing pods but cannot accept new ones.

```bash
kubectl describe node <NODE_NAME>
```

Look for:

```
Unschedulable:      true
```

If the node was cordoned for maintenance and the maintenance is complete, uncordon it:

```bash
kubectl uncordon <NODE_NAME>
```

If you are unsure why the node was cordoned, check events and git history for the cluster configuration before uncordoning.

Refer to [Unschedulable Nodes](https://www.datadoghq.com/blog/debug-kubernetes-pending-pods/#unschedulable-nodes) for further details.

---

## Step 6: Post-Recovery Verification

### Verify Node Is Ready

```bash
kubectl get node <NODE_NAME>
```

Expected output:

```
NAME            STATUS   ROLES    AGE
<NODE_NAME>     Ready    <none>   10d
```

### Verify All Conditions Are Healthy

```bash
kubectl describe node <NODE_NAME> | grep -A 10 "Conditions:"
```

All conditions should show:

| Condition | Expected Status |
|-----------|----------------|
| Ready | True |
| DiskPressure | False |
| MemoryPressure | False |
| PIDPressure | False |
| NetworkUnavailable | False |

### Verify Metrics Are Healthy

Replace the placeholder values with your actual values:
- `<ORG_ID>`: Your organization ID
- `<KUBE_CLUSTER_NAME>`: Your Kubernetes cluster name
- `<NODE_NAME>`: The recovered node name

```promql
# Ready condition should show status="true"
kubernetes_state_node_by_condition{
  condition="Ready",
  kf_node="<NODE_NAME>",
  kube_cluster_name="<KUBE_CLUSTER_NAME>"
}

# All pressure conditions should show status="false"
kubernetes_state_node_by_condition{
  condition=~"MemoryPressure|DiskPressure|PIDPressure|NetworkUnavailable",
  kf_node="<NODE_NAME>",
  kube_cluster_name="<KUBE_CLUSTER_NAME>"
}
```

### Verify Pods Are Scheduling on the Node

```bash
kubectl get pods --all-namespaces --field-selector=spec.nodeName=<NODE_NAME>
```

Confirm that new pods are being scheduled and reaching `Running` state.

---

## Prevention

### Monitor Node Conditions

Ensure the `Node condition not Ready` alert is enabled and covers all pressure conditions in addition to the Ready state.

### Set Resource Requests and Limits

Ensure all workloads specify `resources.requests` and `resources.limits` to prevent any single pod from exhausting node resources:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 1000m
    memory: 1Gi
```

### Configure Kubelet Eviction Thresholds

Tune kubelet eviction thresholds to evict pods before node conditions become critical (values in `kubelet-config`):

```yaml
evictionHard:
  memory.available: "200Mi"
  nodefs.available: "10%"
  nodefs.inodesFree: "5%"
```

### Enable Node Auto-Repair

If using GKE, EKS, or AKS, enable node auto-repair so that persistently unhealthy nodes are automatically replaced by the node pool manager.

### Monitor Disk Usage Trends

```promql
# Alert when node disk usage exceeds 80%
(1 - (node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"})) > 0.8
```

---

## Related Runbooks

- [CrashLoopBackOff Alert](crashloopbackupoff_alert.md) — Pod crash-looping on a node
- [Pod Failed Alert](pod_failed_alert.md) — Pod in Failed state
- [Pinot Segments Unavailable](pinot-segments-unavailable.md) — Downstream impact if Pinot servers are evicted due to node pressure
