# Kfuse Observability Agents Not Running

## Table of Contents

- [Summary](#summary)
- [Symptoms](#symptoms)
- [Step 1: Identify the Affected Node](#step-1-identify-the-affected-node)
- [Step 2: Check Node Health](#step-2-check-node-health)
- [Step 3: Check Agent Pod Status](#step-3-check-agent-pod-status)
- [Step 4: Check Agent Logs](#step-4-check-agent-logs)
- [Step 5: Diagnose Root Cause](#step-5-diagnose-root-cause)
- [Step 6: Post-Recovery Verification](#step-6-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

The Kloudfuse observability agent (`kfuse-agent`) is responsible for collecting metrics, logs, and traces from each host node in the cluster. When the agent stops running on a node, observability data from that host is no longer collected, creating gaps in monitoring coverage.

**Impact:** Metrics, logs, and traces from the affected host will stop flowing into Kloudfuse. Alerts dependent on data from that host may stop firing (false negatives). The gap will persist until the agent is restored.

**Common Root Causes:**
- Agent pod was evicted due to resource pressure (memory or disk) on the node
- Node is unhealthy or has been cordoned — agent pod cannot be scheduled
- Agent pod is crash-looping due to a configuration error or missing secret
- DaemonSet update rolled out a broken image
- Node was added to the cluster but the DaemonSet pod failed to schedule

**Note:** This alert fires when the `kfuse-observability-agent` DaemonSet has fewer ready pods than desired — meaning one or more nodes are missing a running agent. It does not identify the specific node; use the steps below to locate the affected pod(s).

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Symptoms

### Alert Expression

```promql
(
  kubernetes_state_daemonset_desired{
    kfuse="true",
    kube_daemon_set="kfuse-observability-agent"
  }
  -
  kubernetes_state_daemonset_ready{
    kfuse="true",
    kube_daemon_set="kfuse-observability-agent"
  }
) > 0
```

The alert fires when the number of ready pods in the `kfuse-observability-agent` DaemonSet is less than the desired count — meaning one or more nodes in the cluster do not have a running agent pod.

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_state_daemonset_desired` | Equal to node count | — |
| `kubernetes_state_daemonset_ready` | Equal to desired | Less than desired |

**What `kubernetes_state_daemonset_ready` means:** This metric counts pods that are both running and passing their readiness probe. It maps to the Kubernetes DaemonSet status field `numberReady`. A pod must satisfy all three conditions to count as ready:

1. **Scheduled** — the pod has been assigned to a node
2. **Running** — the container has started
3. **Ready** — the readiness probe is passing, indicating the pod is healthy

A pod in `CrashLoopBackOff`, `Pending`, `OOMKilled`, or failing its readiness probe will not count toward `ready`. This means `desired - ready > 0` catches all meaningful failure modes: evicted pods, crash-looping pods, pods stuck in Pending due to resource or taint issues, and pods failing readiness.

**Note:** This alert does not detect a pod that is running and passing its readiness probe but whose agent process has silently stopped reporting metrics. If you suspect silent failure, check `datadog_agent_running` directly for the affected nodes.

---

## Step 1: Identify the Affected Node

The alert label `kf_node` identifies the affected node. Note this value — it is used throughout this runbook.

List all agent pods and their assigned nodes to find the one that is missing or unhealthy:

```bash
kubectl get pods -n kfuse -l app=kfuse-agent -o wide
```

Look for a pod on the affected node that is not in `Running` state, or is absent entirely.

---

## Step 2: Check Node Health

Although the alert only fires for Ready nodes, verify the node is in good health before investigating the agent — resource pressure may have caused an eviction even on an otherwise Ready node:

```bash
kubectl describe node <NODE_NAME> | grep -A 10 "Conditions:"
```

Check for any resource pressure that may have caused an eviction:

```bash
kubectl describe node <NODE_NAME> | grep -E "MemoryPressure|DiskPressure|PIDPressure|Eviction"
```

If the node shows pressure conditions, address those first — see [Node condition not Ready](node_status.md).

---

## Step 3: Check Agent Pod Status

Find the agent pod on the affected node:

```bash
kubectl get pods -n kfuse -l app=kfuse-agent --field-selector=spec.nodeName=<NODE_NAME>
```

If no pod is returned, the DaemonSet failed to schedule on this node. Check why:

```bash
kubectl describe node <NODE_NAME> | grep -A 5 "Taints:"
```

If the pod exists, check its status:

```bash
kubectl describe pod -n kfuse <AGENT_POD_NAME>
```

Look at the `Events` section at the bottom for eviction notices, image pull failures, or OOM kills.

---

## Step 4: Check Agent Logs

If the pod is running but the agent is not reporting:

```bash
kubectl logs -n kfuse <AGENT_POD_NAME> --tail=100
```

If the pod is crash-looping, check the previous container's logs:

```bash
kubectl logs -n kfuse <AGENT_POD_NAME> --previous --tail=100
```

Search Kloudfuse for agent errors across all nodes:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kf_node="<NODE_NAME>" and kube_pod*~"kfuse-agent" and (__kf_level="ERROR" or __kf_level="WARN")
```

---

## Step 5: Diagnose Root Cause

### Case A: Pod Was Evicted

If the pod status shows `Evicted`, the node was under resource pressure when the eviction occurred. The DaemonSet controller should automatically recreate the pod, but it may be stuck if pressure persists.

Check for evicted pods:

```bash
kubectl get pods -n kfuse -l app=kfuse-agent | grep Evicted
```

Delete evicted pods to allow the DaemonSet to reschedule them:

```bash
kubectl delete pod -n kfuse <EVICTED_POD_NAME>
```

Then address the underlying resource pressure on the node — see [Node condition not Ready](node_status.md) and [PV Usage Alert](pv_usage_alert.md).

### Case B: Pod is CrashLoopBackOff

The agent is starting but crashing repeatedly. Check the logs for the root cause:

```bash
kubectl logs -n kfuse <AGENT_POD_NAME> --previous --tail=100
```

Common causes:

| Log Pattern | Likely Cause | Resolution |
|-------------|--------------|------------|
| `missing or invalid API key` | Secret misconfigured | Verify the agent secret is present and correct |
| `permission denied` | RBAC or file permission issue | Check ServiceAccount and ClusterRole bindings |
| `OOMKilled` | Agent memory limit too low | Increase memory limit in DaemonSet spec |
| `failed to connect` | Network policy blocking agent egress | Check NetworkPolicy rules |

For more detail see the [CrashLoopBackOff runbook](crashloopbackupoff_alert.md).

### Case C: Pod Not Scheduled (DaemonSet Missing Pod)

If no pod exists for the affected node, the DaemonSet may be unable to schedule due to a taint or insufficient resources.

Check node taints:

```bash
kubectl describe node <NODE_NAME> | grep Taints
```

If the node has a taint that the DaemonSet tolerates, verify the DaemonSet tolerations:

```bash
kubectl get daemonset -n kfuse kfuse-agent -o jsonpath='{.spec.template.spec.tolerations}' | python3 -m json.tool
```

Check if there are insufficient resources to schedule the pod:

```bash
kubectl describe node <NODE_NAME> | grep -A 5 "Allocated resources"
```

**Resolution:** Add the appropriate toleration to the DaemonSet, or free up resources on the node.

### Case D: DaemonSet Rollout Issue

If the agent stopped running after a recent update, a broken image may have been rolled out.

Check the DaemonSet rollout status:

```bash
kubectl rollout status daemonset/kfuse-agent -n kfuse
```

Check the DaemonSet history:

```bash
kubectl rollout history daemonset/kfuse-agent -n kfuse
```

**Resolution:** Roll back to the previous version if the new image is broken:

```bash
kubectl rollout undo daemonset/kfuse-agent -n kfuse
```

---

## Step 6: Post-Recovery Verification

Verify the agent pod is running on the affected node:

```bash
kubectl get pods -n kfuse -l app=kfuse-agent -o wide | grep <NODE_NAME>
```

Confirm the agent is reporting in Kloudfuse Metrics:

```promql
datadog_agent_running{
  kfuse="true",
  kf_node="<NODE_NAME>"
}
```

Result should be `1`. Also verify that logs and metrics from the host have resumed flowing in Kloudfuse UI.

---

## Prevention

### Monitor Agent Coverage

Ensure all nodes have a running agent:

```promql
count by (kube_cluster_name) (datadog_agent_running{kfuse="true"} == 1)
```

Compare against the total node count to detect gaps.

### Set Appropriate Resource Requests and Limits

Ensure the agent DaemonSet has resource requests set low enough to schedule on all nodes, but limits high enough to avoid OOM kills:

```yaml
resources:
  requests:
    cpu: 100m
    memory: 256Mi
  limits:
    cpu: 500m
    memory: 512Mi
```

### Configure PriorityClass

Give the agent pod a higher priority class to reduce the chance of eviction under resource pressure:

```yaml
priorityClassName: system-node-critical
```

---

## Related Runbooks

- [Node condition not Ready](node_status.md) — Node health issues; this alert only fires when the node is confirmed Ready
- [PV Usage Alert](pv_usage_alert.md) — Disk pressure that may cause agent eviction
- [CrashLoopBackOff Alert](crashloopbackupoff_alert.md) — Pod crash-looping
- [Pod Failed Alert](pod_failed_alert.md) — Pod in Failed state
