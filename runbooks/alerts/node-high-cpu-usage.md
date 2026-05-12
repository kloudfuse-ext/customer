# Node High CPU Usage

## Table of Contents

- [Summary](#summary)
- [Symptoms](#symptoms)
- [Step 1: Identify Affected Nodes](#step-1-identify-affected-nodes)
- [Step 2: Identify Top CPU Consumers](#step-2-identify-top-cpu-consumers)
- [Step 3: Check Logs for Root Cause](#step-3-check-logs-for-root-cause)
- [Step 4: Diagnose Root Cause](#step-4-diagnose-root-cause)
- [Step 5: Remediate](#step-5-remediate)
- [Step 6: Post-Recovery Verification](#step-6-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

This alert fires when the **5-minute average cluster CPU usage reaches 90% or higher** for **5 minutes**. The query uses `avg_over_time` over a 5-minute subquery window to smooth out momentary spikes — the alert only fires when elevated CPU is sustained, not transient.

At 90% utilization, the cluster has limited headroom to absorb additional load. Services begin competing for CPU time, latency rises, and further spikes can push the cluster into saturation.

**Impact:**
- All kfuse services experience increased latency under CPU starvation
- Ingest throughput drops as transformers, ingesters, and parsers slow down
- Query response times increase; queries may time out
- Kubernetes control plane operations (pod scheduling, health checks) may slow
- If CPU saturation persists, liveness probe timeouts can cause pod restarts, creating a cascading failure loop

**Common Root Causes:**
- Sudden traffic spike (e.g., large log burst from a customer environment)
- Kafka consumer lag spike causing all consumers to process at maximum rate simultaneously
- Pinot query serving a very expensive query (full table scan, large aggregation)
- JVM garbage collection storm on multiple services simultaneously
- Deployment rollout increasing total replica count temporarily

---

## Symptoms

### Alert Expression

```promql
avg_over_time(
  (100 - avg by (org_id, kube_cluster_name)(system_cpu_idle{kfuse="true", kf_node!=""}))[5m:30s]
) >= 90
```

This computes the 5-minute rolling average (sampled every 30 seconds) of cluster-average CPU usage. Using `avg_over_time` prevents brief CPU spikes from triggering the alert — the threshold must be sustained over the full window.

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `avg_over_time((100 - system_cpu_idle)[5m:30s])` (cluster average) | `< 80%` | `>= 90%` |
| `system_cpu_iowait` | `< 5%` | `> 20%` (indicates disk I/O bottleneck) |

### Dashboard

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

The **Kloudfuse Cluster** section contains the primary panels for this alert:
- **CPU Usage (per node)** — shows per-node CPU utilization over time; use this to identify which nodes are saturated
- **Memory Usage (per node)** — correlate with CPU to detect nodes under combined resource pressure
- **Service Status** — shows the health of all kfuse services
- **Pods in Failed State** — identifies any pods that have crashed as a result of CPU pressure

---

## Step 1: Identify Affected Nodes

The alert fires on cluster-wide average CPU, so start by identifying which nodes are most saturated.

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

Open the **CPU Usage (per node)** panel. Look for nodes holding consistently above 90% over the alert window. Note the node name(s) — you will use them to correlate with service and log data in subsequent steps.

To query per-node CPU directly in the Metrics explorer:

**Navigate to:** Kloudfuse UI → **Metrics** → **Explorer**

```promql
avg_over_time(
  (100 - system_cpu_idle{kfuse="true", kf_node!=""})[5m:30s]
)
```

Group by `kf_node` to rank nodes by CPU usage.

---

## Step 2: Identify Top CPU Consumers

Once the saturated node(s) are identified, determine which services are driving the load.

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

In the **Service Overview** section, review:
- **Query throughput by Service** — elevated query volume can explain CPU spikes on query-tier nodes
- **Kafka Consumer Lag** — a lag spike means ingest consumers are processing at maximum rate, consuming CPU
- **Pinot Broker Query Execution** — high or slow broker queries indicate expensive query workloads
- **Metric samples per second / Log lines per second / Trace ingester spans per second** — sudden ingestion rate increases drive transformer and ingester CPU

To break down CPU usage by service in the Metrics explorer:

**Navigate to:** Kloudfuse UI → **Metrics** → **Explorer**

```promql
avg by (kube_deployment)(
  system_cpu_user{kfuse="true", kube_namespace="kfuse"}
)
```

Look for a single deployment or statefulset consuming disproportionately more CPU than others.

---

## Step 3: Check Logs for Root Cause

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

Search for errors and warnings across the kfuse namespace around the time the alert fired:

```
kube_namespace="kfuse" and level=~"warn|error"
```

For JVM-based services (Pinot, Kafka) — GC storms appear here:

```
kube_namespace="kfuse" and ("GC overhead" or "Full GC" or "stop-the-world" or "OutOfMemoryError")
```

For Kafka consumer lag spikes and rebalances:

```
kube_stateful_set=~"kafka-kraft-broker|ingester" and ("lag" or "rebalance" or "catch up")
```

For expensive or slow Pinot queries:

```
kube_stateful_set=~"pinot-server-realtime|pinot-server-offline" and ("query" or "timeout" or "slow" or "Exception")
```

---

## Step 4: Diagnose Root Cause

### Case A: Ingest Traffic Spike

A sudden burst of incoming data (e.g., a noisy log source, a new application deployment with verbose logging) causes transformers and ingesters to run at maximum CPU.

Check ingest rates in the Kloudfuse Overview dashboard:

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

Review the **Stream Overview** section — look for a sharp uptick in:
- **Log lines per second**
- **Metric samples per second**
- **Trace ingester spans per second throughput**

Correlate the timing of the spike with the alert firing time.

**Resolution:** If the traffic spike is unexpected and unsustainable, throttle ingestion via Rate Control:

**Navigate to:** Kloudfuse UI → **Admin** → **Rate Control**

Reduce the ingestion rate limit for the affected stream or add a drop rule for the noisy source. If the ingest load needs to be stopped entirely while investigating, see [Stop Queries and Ingestion](../stop-queries-and-ingestion.md).

### Case B: Kafka Consumer Lag Spike

When Kafka consumer lag grows (e.g., after a slow period or a burst of data), all Kafka consumers (ingesters, transformers) process at maximum CPU rate simultaneously to catch up.

Check Kafka consumer lag in the Kloudfuse Overview dashboard:

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

Open the **Kafka Consumer Lag** panel. Lag growing over time indicates ingest is outpacing processing capacity.

Confirm the trend in the Metrics explorer:

```promql
# Positive values mean lag is growing (ongoing overload)
# Negative values mean lag is decreasing (catch-up in progress)
increase(kafka_consumergroup_lag{kfuse="true"}[5m])
```

**Resolution if lag is decreasing:** The cluster is catching up from a burst — monitor until lag returns to zero and CPU normalises. No action required.

**Resolution if lag is growing:** Ingest rate is exceeding processing capacity. Throttle ingestion via Rate Control or stop ingestion temporarily:

**Navigate to:** Kloudfuse UI → **Admin** → **Rate Control**

Or follow [Stop Queries and Ingestion](../stop-queries-and-ingestion.md) to halt ingestion while the cluster recovers.

### Case C: Expensive or Runaway Query

A full table scan or large aggregation on Pinot servers can saturate CPU on query-tier nodes. Long-running queries also hold server threads, blocking other queries.

Check for query load in the Kloudfuse Overview dashboard:

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

Review the **Service Overview** section:
- **Pinot Broker Query Execution** — high execution time or query volume indicates an expensive query workload
- **Query throughput by Service** — identify which query service (logs, metrics, traces) is generating the load
- **Query Service Error Count** — timeouts and errors often accompany runaway queries

Identify the specific queries driving load by searching logs:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_deployment=~"query-service|trace-query-service|logs-query-service" and ("slow" or "timeout" or "Exception" or "took")
```

For a deeper investigation of what queries are running and which are expensive, use the **MCP Server** to analyse query patterns, execution plans, and current active queries across the Pinot cluster.

**Resolution:** If a runaway query is identified, stop queries for the affected service to immediately relieve CPU pressure, then investigate the query pattern:

Follow [Stop Queries and Ingestion](../stop-queries-and-ingestion.md) to stop the relevant query service.

### Case D: JVM Garbage Collection Storm

Multiple JVM-based services (Pinot, Kafka) running full GC simultaneously cause cluster-wide CPU spikes as the JVM pauses threads and reclaims heap.

Check for GC events in Kloudfuse logs:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_namespace="kfuse" and ("Full GC" or "GC pause" or "GC overhead limit exceeded" or "stop-the-world")
```

If multiple services are logging GC events simultaneously, heap sizes are too small for current load. This is a configuration issue that requires a Helm values update — contact Kloudfuse support to tune JVM heap settings appropriately.

---

## Step 5: Remediate

The appropriate remediation depends on the root cause identified in Step 4. The primary levers available are:

### Option 1: Throttle Ingestion via Rate Control

If an ingest traffic spike is driving CPU, reduce or temporarily halt ingestion without stopping query services:

**Navigate to:** Kloudfuse UI → **Admin** → **Rate Control**

Lower the ingestion rate limit for the affected stream, or add a drop rule for the specific noisy source. This is the least disruptive option and allows queries to continue serving existing data.

### Option 2: Stop Queries and/or Ingestion

If query load or ingestion is saturating the cluster and cannot be throttled sufficiently via Rate Control, follow the [Stop Queries and Ingestion](../stop-queries-and-ingestion.md) runbook to:

- Stop specific query services to relieve CPU on query-tier nodes
- Stop ingestion at the ingress level to halt all incoming data

> **Note:** Stopping ingestion drops incoming data for the duration. Stopping queries makes the UI and API unavailable for that signal type. Use the minimum intervention necessary.

---

## Step 6: Post-Recovery Verification

### Verify CPU Usage Has Dropped

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

Open the **CPU Usage (per node)** panel and confirm all nodes have returned below 80%.

Verify the alert expression has resolved in the Metrics explorer:

```promql
avg_over_time(
  (100 - avg by (org_id, kube_cluster_name)(system_cpu_idle{kfuse="true", kf_node!=""}))[5m:30s]
)
```

Should be well below 90%.

### Verify Service Health

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

Check the **Service Status** and **Pods in Failed State** panels. All services should be healthy with no pods in a failed state.

### Verify Kafka Lag Has Recovered

In the **Kloudfuse Overview** dashboard, check the **Kafka Consumer Lag** panel. Lag should be at or trending toward zero.

```promql
kafka_consumergroup_lag{kfuse="true"}
```

### Verify Query and Ingest Throughput

If queries or ingestion were stopped as part of remediation, confirm they have been restored:

**Navigate to:** Kloudfuse UI → **Dashboards** → **CP Dashboards** → **Kloudfuse Overview**

Confirm the **Stream Overview** ingestion rate panels and **Query throughput by Service** panel show traffic flowing again.

---

## Prevention

### Monitor Kafka Consumer Lag as a Leading Indicator

Consumer lag growth is often the earliest signal of an impending CPU saturation event. Alert on growing lag before it causes a CPU crisis:

```promql
increase(kafka_consumergroup_lag{kfuse="true"}[10m]) > 100000
```

### Alert Earlier on CPU Trends

Add a warning alert before the 90% critical threshold to allow time for investigation before the situation becomes urgent:

```promql
# Warning alert at 80%
avg_over_time(
  (100 - avg by (org_id, kube_cluster_name)(system_cpu_idle{kfuse="true", kf_node!=""}))[5m:30s]
) > 80
```

### Configure Rate Control Headroom

Set ingestion rate limits conservatively — at a level that leaves 20–30% CPU headroom — so that traffic spikes can be absorbed without saturating the cluster. Review rate limits regularly as ingestion volumes grow.

---

## Related Runbooks

- [Stop Queries and Ingestion](../stop-queries-and-ingestion.md) — Stop query services or halt ingestion to relieve CPU pressure
- [Node condition not Ready](node_status.md) — Node conditions that may accompany CPU saturation
- [Kfuse Ingest Service Availability](kfuse-ingest-service-availability.md) — Ingest components that may crash under sustained CPU pressure
- [Kfuse Query Service Availability](kfuse-query-service-availability.md) — Query components affected by CPU saturation
- [Rate Control Limit Reached](rate-control-limit-reached.md) — Managing ingestion rate to prevent ingest-driven CPU spikes
