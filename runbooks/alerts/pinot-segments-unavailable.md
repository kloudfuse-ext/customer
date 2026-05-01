# Pinot Segments Unavailable

## Table of Contents

- [Summary](#summary)
- [Symptoms](#symptoms)
- [Step 1: Verify Pod Health](#step-1-verify-pod-health)
- [Step 2: Check Pinot Server Logs](#step-2-check-pinot-server-logs)
- [Step 3: Identify Affected Tables and Segments](#step-3-identify-affected-tables-and-segments)
- [Step 4: Diagnose Root Cause](#step-4-diagnose-root-cause)
- [Step 5: Reload Segments](#step-5-reload-segments)
- [Step 6: Reset REALTIME Segment Consumption](#step-6-reset-realtime-segment-consumption-if-kafka-data-is-available)
- [Step 7: Post-Recovery Verification](#step-7-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

When Apache Pinot segments are reported as unavailable, queries against those tables will return partial results or fail with "No server found for segment" errors. This runbook provides steps to identify the root cause and restore segment availability.

**Impact:** Queries against affected tables return incomplete or no data. Real-time ingestion may also be impacted if consuming segments are affected.

**Common Root Causes:**

This alert fires when `pinot_controller_percentSegmentsAvailable_Value < 90` averaged over 10 minutes. This metric drops below 100% in several scenarios — not all of which require immediate intervention:

- Segments in ERROR state (hard failure — requires action)
- Segments still loading/downloading after a server restart (transient — will self-resolve)
- Segments being relocated between servers (transient — will self-resolve)
- REALTIME segments temporarily catching up on consumption (transient — will self-resolve)
- Deep store (S3/GCS/Azure Blob) connectivity or permissions issues preventing segment download
- Segment corruption in deep store or on the server
- ZooKeeper state mismatch — controller believes a segment is assigned to a server that can't serve it

**Note:** If segments are in hard ERROR state, the [Pinot Segments in Error State](pinot-segments-in-error-state.md) alert will also fire with more specific details.

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Symptoms

### Query Errors

Queries to Pinot (via broker) may return errors such as:

```
ProcessingException(errorCode:210, message:No server found for segment: <table_OFFLINE_segment_name>)
```

```
QueryException: Encountered errors when executing the query...
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `pinot_controller_percentSegmentsAvailable_Value` | `100` | `< 90` |
| `pinot_controller_segmentsInErrorState_Value` | `0` | `> 0` |
| `pinot_controller_validation_missingSegmentCount_Value` | `0` | `> 0` |

### Alert Expression

```promql
avg by (org_id, kube_cluster_name, kf_node, table) (
  avg_over_time(
    pinot_controller_percentSegmentsAvailable_Value{
      kfuse="true",
      kube_service="pinot-controller",
      table=~"kf_logs|kf_metrics|kf_metrics_rollup"
    }[10m]
  ) < 100
)
unless on (org_id, kube_cluster_name, kf_node)
(
  sum by (org_id, kube_cluster_name, kf_node) (
    kubernetes_state_node_by_condition{
      kfuse="true",
      condition="Ready",
      status=~"false|unknown",
      kf_node=~".+"
    }
  ) > 0
)
```

**Note:** The alert is suppressed when the Pinot controller node itself is not Ready — in that case the [Node condition not Ready](node_status.md) alert will fire instead.

---

## Step 1: Verify Pod Health

Check the status of all Pinot pods:

```bash
kubectl get pods -n kfuse | grep pinot
```

Expected output — all pods should show `Running` with all containers ready:

```
pinot-broker-0                          1/1     Running   0          2d
pinot-controller-0                      1/1     Running   0          2d
pinot-server-0                          1/1     Running   0          2d
pinot-server-1                          1/1     Running   0          2d
pinot-server-2                          1/1     Running   0          2d
pinot-zookeeper-0                       1/1     Running   0          2d
pinot-zookeeper-1                       1/1     Running   0          2d
pinot-zookeeper-2                       1/1     Running   0          2d
```

If any pod is **not** Running or shows restarts, address pod health first:

- For `CrashLoopBackOff` → see the [CrashLoopBackOff runbook](crashloopbackupoff_alert.md)
- For `ImagePullBackOff` → see the [ImagePullBackOff runbook](imagepullbackoff_alert.md)
- For ZooKeeper issues → see the [Pinot ZooKeeper Corruption Recovery runbook](pinot-zookeeper-corruption-recovery.md)

---

## Step 2: Check Pinot Server Logs

Identify which server is reporting errors by searching Pinot server logs in Kloudfuse.

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

Set the time range to cover when the alert fired, then run the following FuseQL query:

```
kube_pod*~"pinot-server" and (__kf_level="ERROR" or __kf_level="WARN")
```

To narrow down to segment-specific failures:

```
kube_pod*~"pinot-server" and ("Failed to load" or "Failed to download" or "Cannot find" or "unavailable" or "segment")
```

Review the results grouped by `kube_pod` to identify which server instance is generating the errors.

Common error patterns to look for:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `Failed to download segment` | Deep store connectivity issue |
| `Segment not found in deep store` | Segment corrupted or missing from deep store |
| `Failed to load segment` | Local disk issue or segment corruption |
| `ZooKeeper connection lost` | ZooKeeper instability |
| `OutOfMemoryError` | Server OOM — needs resource increase |

---

## Step 3: Identify Affected Tables and Segments

Use the [segments-error.sh](../../scripts/alerts/segments-error.sh) script to list all tables with non-ONLINE segments, or check a specific table:

```bash
# Scan all tables for non-ONLINE segments
./segments-error.sh status

# Check a specific table
./segments-error.sh status kf_logs_REALTIME
```

---

## Step 4: Diagnose Root Cause

Use the script to show segment states and server assignments side-by-side:

```bash
./segments-error.sh diagnose <TABLE_NAME>
```

Review the output to identify which servers have non-ONLINE segments, then match to one of the cases below.

### Case A: Server Was Recently Restarted (Segments Still Loading)

After a server restart, Pinot must re-download segments from deep store. This can take several minutes depending on segment size and count.

Check if segments are actively loading in Kloudfuse.

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod*~"pinot-server" and ("Downloading" or "Loading segment" or "Loaded segment")
```

If you see a steady stream of `Loaded segment` messages, the server is still recovering — wait for it to complete.

**Resolution:** Wait for segments to finish loading. Monitor with:

```bash
CONTROLLER_POD=$(kubectl get pods -n kfuse -l app=pinot-controller -o jsonpath='{.items[0].metadata.name}')

watch -n 30 "kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s \"http://localhost:9000/tables/<TABLE_NAME>/segments\" | \
  python3 -c \"import sys,json; data=json.load(sys.stdin); print(data)\""
```

### Case B: Deep Store Connectivity Issue

If servers cannot download segments from deep store (S3, GCS, Azure), search for download errors in Kloudfuse.

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod*~"pinot-server" and ("Failed to download" or "Connection refused" or "Access Denied" or "NoSuchKey" or "404")
```

If you see `Access Denied` or `403` errors, check the Pinot server's IAM role or service account credentials.

If you see `NoSuchKey` or `404` errors, the segment may be missing from deep store — proceed to **Case D**.

**Resolution:** Fix deep store credentials or network connectivity. Then trigger a segment reload (see Step 5).

### Case C: Single Server is Unhealthy

If only one server is reporting errors and others are healthy, the replication factor may absorb the impact.

Check which server has the problem:

```bash
CONTROLLER_POD=$(kubectl get pods -n kfuse -l app=pinot-controller -o jsonpath='{.items[0].metadata.name}')

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/<TABLE_NAME>/externalview" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
servers = {}
for table_type in ('OFFLINE', 'REALTIME'):
    for seg, assignments in data.get(table_type, {}).items():
        for server, state in assignments.items():
            if state != 'ONLINE':
                servers.setdefault(server, []).append((seg, state))
for server, issues in servers.items():
    print(f'{server}: {len(issues)} segments not ONLINE')
"
```

**Resolution:** Restart the unhealthy server pod:

```bash
# Replace <SERVER_POD_NAME> with the affected pod (e.g., pinot-server-1)
kubectl delete pod -n kfuse <SERVER_POD_NAME>

# Wait for it to be ready
kubectl wait --for=condition=Ready pod/<SERVER_POD_NAME> -n kfuse --timeout=600s
```

### Case D: Segment Corrupted or Missing from Deep Store

If a segment is missing from deep store and was not replicated, it may not be recoverable. However, for REALTIME tables, Pinot can rebuild segments from Kafka if offset retention permits.

Check if the segment exists in deep store (the path depends on your deep store configuration — check `pinot-server` config for `pinot.server.instance.dataManagerClass` and deep store URI):

```bash
# For S3 deep store — replace bucket/path with your configuration
aws s3 ls s3://<BUCKET>/pinot/<TABLE_NAME>/<SEGMENT_NAME>/

# For GCS deep store — replace bucket/path with your configuration
gsutil ls gs://<BUCKET>/pinot/<TABLE_NAME>/<SEGMENT_NAME>/
```

If the segment is confirmed missing or corrupted:

- For **OFFLINE** tables: the data for that time range is lost unless a backup exists.
- For **REALTIME** tables: if Kafka retention covers the missing segment's time range, the segment can be rebuilt by resetting the segment consumption offset (see Step 6).

---

## Step 5: Reload Segments

If segments are in ERROR state and the underlying cause (connectivity, server health) is resolved, trigger a reload. The script will automatically re-check segment states after the reload:

```bash
# Reload all segments for a table
./segments-error.sh reload <TABLE_NAME>

# Reload a single segment
./segments-error.sh reload <TABLE_NAME> <SEGMENT_NAME>
```

---

## Step 6: Reset REALTIME Segment Consumption (If Kafka Data Is Available)

If a REALTIME segment is stuck in ERROR and Kafka still has the data, reset the consuming segment to restart ingestion from the correct offset.

> **Warning:** Only use this for REALTIME tables. Resetting a consuming segment that has already been committed may cause data duplication or loss if done incorrectly. Confirm with your team before proceeding.

First use `status` to identify which segments are in ERROR, then use `reset`:

```bash
./segments-error.sh status <TABLE_NAME>_REALTIME

./segments-error.sh reset <TABLE_NAME>_REALTIME <SEGMENT_NAME>
```

The script will prompt for confirmation before resetting. After reset, monitor consumption resuming in Kloudfuse:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod*~"pinot-server" and "<SEGMENT_NAME>"
```

---

## Step 7: Post-Recovery Verification

Run the verify command to check segment health, run a broker query test, and print the PromQL queries to confirm in Kloudfuse Metrics:

```bash
./segments-error.sh verify <TABLE_NAME>
```

A healthy result shows all segments `ONLINE`, `numServersQueried` matching `numServersResponded` with no exceptions, and the PromQL expressions returning `0`.

---

## Prevention

### Monitor Segment Error Count

```promql
pinot_controller_numSegmentsWithError{org_id="<ORG_ID>"} > 0
```

### Monitor Server Restarts

Frequent server restarts cause repeated segment reload delays:

```promql
increase(kube_pod_container_status_restarts_total{namespace="kfuse", pod=~"pinot-server.*"}[1h]) > 2
```

### Ensure Adequate Server Resources

Segment load failures from OOM are prevented by tuning the server heap size. Use `jvmMemory` in `values.yaml` — specify an integer followed by `G`:

```yaml
server:
  jvmMemory: 8G
```

---

## Related Runbooks

- [Pinot Segments in Error State](pinot-segments-in-error-state.md) — Hard segment ERROR failures requiring intervention
- [Node condition not Ready](node_status.md) — Node-level failures that may suppress this alert
- [Pinot ZooKeeper Corruption Recovery](pinot-zookeeper-corruption-recovery.md) — ZooKeeper quorum loss affecting Pinot state
- [CrashLoopBackOff Alert](crashloopbackupoff_alert.md) — Pod crash-looping
- [Pod Failed Alert](pod_failed_alert.md) — Pod in Failed state
