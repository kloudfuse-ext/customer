# Kfuse Ingest Service Availability

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

The ingest service availability alerts fire when one or more pods in the Kloudfuse data ingestion pipeline become unavailable. This covers the full pipeline from data ingress (Envoy, Nginx) through transformation (logs, metrics, traces) to storage (Kafka, Redis, PostgreSQL).

**Impact:** Depending on the affected component:
- **Envoy / Nginx / Pushgateway:** Data from agents and exporters cannot reach the platform; ingestion stops for all signal types.
- **Logs/Metrics/Trace Transformer:** Transformed data is not written to Kafka; that signal type stops flowing into storage.
- **Ingester:** Data written to Kafka is not consumed into Pinot; queries will return stale data.
- **Kafka (broker or controller):** All data ingestion buffers halt; data may be lost if Kafka retention is exceeded.
- **Redis:** Cache unavailability can degrade ingest throughput and transformer coordination.
- **Orchestrator PostgreSQL:** Rate control and job scheduling may fail, impacting ingestion throttling.
- **Profiler Server:** Profiling data ingestion stops.

**Common Root Causes:**
- Pod OOMKilled due to insufficient memory limits
- Node pressure causing pod eviction (see [Node condition not Ready](node_status.md))
- PVC full on Kafka or Redis (see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md))
- Container image pull failure after a deployment
- Application crash or deadlock — check pod logs for panics/exceptions
- Resource quota exhaustion in the `kfuse` namespace

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Affected Components

### Alert: Kfuse-ingest deployment pods are unavailable (Critical)
Fires when **1 or more** replicas are unavailable for **10 minutes**.

| Deployment | Role |
|------------|------|
| `envoy-gateway` | API gateway — routes inbound data from agents and exporters |
| `kfuse-pushgateway` | Prometheus push gateway — receives pushed metrics |
| `kfuse-ingress-nginx-controller` | Nginx ingress controller — terminates external HTTP/S traffic |

### Alert: Kfuse-ingest scalable deployment pods are unavailable (Critical)
Fires when **3 or more** replicas are unavailable (or **4+** if desired >= 11) for **10 minutes**.

| Deployment | Role |
|------------|------|
| `logs-transformer` | Normalizes and transforms log data before writing to Kafka |
| `metrics-transformer` | Normalizes and transforms metrics data before writing to Kafka |
| `trace-transformer` | Normalizes and transforms trace/APM data before writing to Kafka |

### Alert: Kfuse-ingest statefulset pods are unavailable (Critical)
Fires when **1 or more** replicas are unavailable for **10 minutes**.

| StatefulSet | Role |
|-------------|------|
| `kfuse-redis` | Redis cache — used for transformer coordination and rate control |
| `kfuse-profiler-server` | Receives and stores profiling (pyroscope) data |
| `orchestrator-postgresql` | PostgreSQL — backs orchestrator for rate control and job scheduling |

### Alert: Kfuse-ingest scalable statefulset pods are unavailable (Critical)
Fires when **3 or more** replicas are unavailable (or **4+** if desired >= 11) for **10 minutes**.

| StatefulSet | Role |
|-------------|------|
| `ingester` | Core ingester — consumes from Kafka and writes to Pinot |
| `kafka-kraft-broker` | Kafka message broker — buffers all incoming telemetry data |
| `kafka-kraft-controller` | Kafka KRaft controller — manages broker cluster metadata |
| `logs-parser` | Parses structured log data from Kafka topics |

---

## Symptoms

### Alert Expressions

**Deployment — non-scalable (1+ unavailable):**
```promql
sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
  kubernetes_state_deployment_replicas_desired{
    kube_app_instance="kfuse",
    kube_deployment=~"envoy-gateway|kfuse-pushgateway|kfuse-ingress-nginx-controller"
  }
) - sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
  kubernetes_state_deployment_replicas_available{
    kube_app_instance="kfuse",
    kube_deployment=~"envoy-gateway|kfuse-pushgateway|kfuse-ingress-nginx-controller"
  }
) > 0
```

**Scalable deployment (3+ unavailable):**
```promql
(
  sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
    kubernetes_state_deployment_replicas_desired{
      kube_app_instance="kfuse",
      kube_deployment=~"logs-transformer|metrics-transformer|trace-transformer"
    }
  ) - sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
    kubernetes_state_deployment_replicas_available{
      kube_app_instance="kfuse",
      kube_deployment=~"logs-transformer|metrics-transformer|trace-transformer"
    }
  )
) >= (3 + (
  sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
    kubernetes_state_deployment_replicas_desired{
      kube_app_instance="kfuse",
      kube_deployment=~"logs-transformer|metrics-transformer|trace-transformer"
    }
  ) >=bool 11
))
```

**StatefulSet — non-scalable (1+ unavailable):**
```promql
sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
  kubernetes_state_statefulset_replicas_desired{
    kube_app_instance="kfuse",
    kube_stateful_set=~"kfuse-redis|kfuse-profiler-server|orchestrator-postgresql"
  }
) - sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
  kubernetes_state_statefulset_replicas_ready{
    kube_app_instance="kfuse",
    kube_stateful_set=~"kfuse-redis|kfuse-profiler-server|orchestrator-postgresql"
  }
) > 0
```

**Scalable statefulset (3+ unavailable):**
```promql
(
  sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
    kubernetes_state_statefulset_replicas_desired{
      kube_app_instance="kfuse",
      kube_stateful_set=~"ingester|kafka-kraft-broker|kafka-kraft-controller|logs-parser"
    }
  ) - sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
    kubernetes_state_statefulset_replicas_ready{
      kube_app_instance="kfuse",
      kube_stateful_set=~"ingester|kafka-kraft-broker|kafka-kraft-controller|logs-parser"
    }
  )
) >= (3 + (
  sum by (org_id, kube_cluster_name, kube_namespace, kube_stateful_set)(
    kubernetes_state_statefulset_replicas_desired{
      kube_app_instance="kfuse",
      kube_stateful_set=~"ingester|kafka-kraft-broker|kafka-kraft-controller|logs-parser"
    }
  ) >=bool 11
))
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_state_deployment_replicas_desired - kubernetes_state_deployment_replicas_available` | `0` | `>= 1` (non-scalable) or `>= 3` (scalable) |
| `kubernetes_state_statefulset_replicas_desired - kubernetes_state_statefulset_replicas_ready` | `0` | `>= 1` (non-scalable) or `>= 3` (scalable) |

### Dashboard

Navigate to: Kloudfuse UI → **Dashboards** → **CP Dashboards** → **kfuse-cp** to see an overview of control plane component health.

For Kafka-specific metrics: **Dashboards** → **CP Dashboards** → **kafka**

---

## Step 1: Identify the Affected Component

The alert `description` label will identify the specific `kube_deployment` or `kube_stateful_set` that is unavailable. Check the alert details in the Kloudfuse UI or your notification channel to find:

- **Deployment name** (for deployment alerts)
- **StatefulSet name** (for statefulset alerts)
- **Namespace** and **cluster name**

Then list all pods for that component:

```bash
# For a deployment (e.g., logs-transformer)
kubectl get pods -n kfuse -l app=<DEPLOYMENT_NAME>

# For a statefulset (e.g., kafka-kraft-broker)
kubectl get pods -n kfuse -l app=<STATEFULSET_NAME>

# Or search by name
kubectl get pods -n kfuse | grep <COMPONENT_NAME>
```

Look for pods in states other than `Running` — common problem states:

| Pod State | Meaning |
|-----------|---------|
| `Pending` | Pod cannot be scheduled — node resources or PVC unavailable |
| `CrashLoopBackOff` | Container is crashing repeatedly on startup |
| `OOMKilled` | Container was killed due to memory limit exceeded |
| `ImagePullBackOff` | Container image cannot be pulled |
| `Terminating` (stuck) | Pod is stuck terminating — may indicate node issue |

---

## Step 2: Check Pod Status and Events

Describe the affected pod to see resource constraints, node assignment, and events:

```bash
kubectl describe pod -n kfuse <POD_NAME>
```

In the output, check:
- **Events** section at the bottom for scheduling failures, OOM kills, or pull errors
- **Node** field — if the node is unhealthy, see the [Node condition not Ready](node_status.md) runbook
- **Containers / State** — look for `OOMKilled`, `Error`, or `Waiting` with a reason

Check recent events across the namespace:

```bash
kubectl get events -n kfuse --sort-by='.lastTimestamp' | grep -E "Warning|Failed|OOM|Evict" | tail -30
```

---

## Step 3: Check Logs for Root Cause

Search for errors in the affected component's logs via the Kloudfuse UI.

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

Set the time range to cover when the alert fired, then search:

```
kube_deployment="<DEPLOYMENT_NAME>" and level=~"error|fatal"
```

Or for statefulsets:

```
kube_stateful_set="<STATEFULSET_NAME>" and level=~"error|fatal"
```

Common patterns to look for:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `OutOfMemoryError` or `java.lang.OutOfMemoryError` | JVM heap exhausted — increase memory limits |
| `panic:` or `fatal error:` | Application crash — check for recent deployments |
| `connection refused` to Kafka | Kafka brokers unavailable |
| `FATAL: database` or `could not connect to PostgreSQL` | PostgreSQL down |
| `Failed to connect to Redis` | Redis unavailable |
| `no space left on device` | PVC full — see [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) |

For logs from a pod that has already restarted, filter by time range in the Kloudfuse Logs Search UI to cover the window before the restart:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod="<POD_NAME>" and level=~"error|fatal"
```

---

## Step 4: Diagnose Root Cause

### Case A: Kafka Broker or Controller Unavailable

Kafka is the central message bus. Loss of multiple brokers will cause all transformers and ingesters to stall waiting for broker leadership.

Check Kafka broker health:

```bash
kubectl get pods -n kfuse | grep kafka
```

If brokers are crashing, check for PVC capacity issues:

```bash
kubectl get pvc -n kfuse | grep kafka
```

If PVCs are near capacity, follow the [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) runbook.

For KRaft controller issues, check that a controller quorum exists — at least 2 of 3 controllers must be Running.

### Case B: Ingester Unavailable

The ingester consumes from Kafka and writes to Pinot. If ingesters are down, Kafka topics will grow and Pinot data will be delayed.

Check ingester-specific errors in Kloudfuse:

```
kube_stateful_set="ingester" and ("failed" or "error" or "kafka" or "pinot")
```

Ingesters depend on both Kafka and Pinot being healthy. If Pinot is the issue, check the [Pinot Segments Unavailable](pinot-segments-unavailable.md) runbook.

### Case C: Transformer Unavailable (logs/metrics/trace)

Transformers are stateless and horizontally scalable. If 3+ are unavailable, throughput is severely degraded but the pipeline is not fully blocked until all replicas are down.

Check if this is a node-level issue (multiple pods evicted from one node):

```bash
kubectl get pods -n kfuse -o wide | grep transformer | grep -v Running
```

If pods are spread across failed nodes, address the node first: [Node condition not Ready](node_status.md).

### Case D: Envoy / Nginx / Pushgateway Unavailable

These are the external ingress components. If they are down, agents cannot send data to the platform.

Check ingress status:

```bash
kubectl get pods -n kfuse | grep -E "envoy-gateway|ingress-nginx|pushgateway"
kubectl get svc -n kfuse | grep -E "envoy|ingress|pushgateway"
```

### Case E: Pod Stuck in Pending

```bash
kubectl describe pod -n kfuse <POD_NAME> | grep -A 10 "Events:"
```

Common reasons:
- **Insufficient CPU/memory:** Add nodes or adjust resource requests
- **PVC not bound:** Check `kubectl get pvc -n kfuse`
- **Node selector / affinity:** Check if nodes matching the pod's affinity exist

---

## Step 5: Restart the Affected Component

After resolving the underlying cause (PVC full, node pressure, etc.), restart the affected component:

**For a Deployment:**

```bash
kubectl rollout restart deployment/<DEPLOYMENT_NAME> -n kfuse

# Monitor rollout
kubectl rollout status deployment/<DEPLOYMENT_NAME> -n kfuse
```

**For a StatefulSet:**

```bash
kubectl rollout restart statefulset/<STATEFULSET_NAME> -n kfuse

# Monitor rollout
kubectl rollout status statefulset/<STATEFULSET_NAME> -n kfuse
```

**For a single crashing pod (force recreate):**

```bash
kubectl delete pod -n kfuse <POD_NAME>
# Kubernetes will recreate it automatically
kubectl get pods -n kfuse | grep <COMPONENT_NAME>
```

---

## Step 6: Post-Recovery Verification

### Verify All Pods Are Running

```bash
# Check all ingest-related pods
kubectl get pods -n kfuse | grep -E "envoy-gateway|pushgateway|ingress-nginx|logs-transformer|metrics-transformer|trace-transformer|kfuse-redis|kfuse-profiler|orchestrator-postgresql|ingester|kafka-kraft|logs-parser"
```

All pods should show `Running` with all containers ready (e.g., `1/1`).

### Verify Kafka Broker Health

```bash
KAFKA_POD=$(kubectl get pods -n kfuse -l app=kafka-kraft-broker -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n kfuse $KAFKA_POD -- kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Verify Data Is Flowing

Check in the Kloudfuse UI that new logs, metrics, and traces are arriving:

**Navigate to:** Kloudfuse UI → **Logs** → **Live Tail**

Confirm that new log lines are appearing. Similarly, check **Metrics** → **Explorer** for recent data points.

You can also verify via PromQL that replicas are back to desired:

```promql
# Should return 0 for all deployments
sum by (kube_deployment)(
  kubernetes_state_deployment_replicas_desired{kube_app_instance="kfuse",
    kube_deployment=~"envoy-gateway|kfuse-pushgateway|kfuse-ingress-nginx-controller|logs-transformer|metrics-transformer|trace-transformer"
  }
) - sum by (kube_deployment)(
  kubernetes_state_deployment_replicas_available{kube_app_instance="kfuse",
    kube_deployment=~"envoy-gateway|kfuse-pushgateway|kfuse-ingress-nginx-controller|logs-transformer|metrics-transformer|trace-transformer"
  }
)
```

---

## Prevention

### Set Appropriate Resource Requests and Limits

Ensure all ingest components have memory limits set to prevent OOM conditions from starving other pods:

```yaml
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    memory: 2Gi
```

### Monitor Kafka Consumer Lag

Elevated consumer lag is an early warning of ingester or transformer capacity problems. Alert on it before pods begin crashing:

```promql
kafka_consumergroup_lag{kfuse="true"} > 100000
```

### Monitor PVC Capacity for Kafka

```promql
(
  max by (persistentvolumeclaim)(kubernetes_kubelet_volume_stats_used_bytes{kfuse="true"})
  * 100
  / max by (persistentvolumeclaim)(kubernetes_kubelet_volume_stats_capacity_bytes{kfuse="true"})
) > 80
```

Alert at 80% so you have time to expand before the 90% alert fires.

---

## Related Runbooks

- [Kfuse Query Service Availability](kfuse-query-service-availability.md) — Query-side unavailability downstream of ingest
- [Pinot Segments Unavailable](pinot-segments-unavailable.md) — Pinot segment issues caused by ingester failures
- [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) — PVC full issues affecting Kafka or Redis
- [Node condition not Ready](node_status.md) — Node-level failures causing pod evictions
- [Kfuse Zookeeper Quorum Alert](kfuse-zookeeper-quorum-alert.md) — ZooKeeper loss affecting Pinot coordination
