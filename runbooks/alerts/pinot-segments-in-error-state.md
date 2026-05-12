# Pinot Segments in Error State

## Table of Contents

- [Summary](#summary)
- [Symptoms](#symptoms)
- [Step 1: Identify the Affected Node and Table](#step-1-identify-the-affected-node-and-table)
- [Step 2: Identify Segments in ERROR State](#step-2-identify-segments-in-error-state)
- [Step 3: Check Pinot Server Logs](#step-3-check-pinot-server-logs)
- [Step 4: Diagnose Root Cause](#step-4-diagnose-root-cause)
- [Step 5: Reload Segments](#step-5-reload-segments)
- [Step 6: Reset REALTIME Segment Consumption](#step-6-reset-realtime-segment-consumption-if-kafka-data-is-available)
- [Step 7: Post-Recovery Verification](#step-7-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

When Apache Pinot segments are in an ERROR state, the controller has determined that a segment cannot be served from its assigned server. Unlike partial unavailability (where segments may be loading or relocating), an ERROR state indicates a hard failure that will not self-resolve without intervention.

**Impact:** Queries against affected tables (`kf_logs`, `kf_metrics`, `kf_metrics_rollup`) will return incomplete data or fail with no-server errors for the affected segments.

**Common Root Causes:**
- Pinot server failed to download a segment from deep store (S3/GCS/Azure) due to connectivity or permissions issues
- Segment is corrupted in deep store or on the server's local disk
- Server ran out of disk space or memory while loading the segment
- ZooKeeper state mismatch — controller assigned a segment to a server that cannot serve it
- Server pod was replaced and segments have not yet reloaded

**Note:** This metric is updated by the Pinot controller every 5 minutes, so there may be a short lag between when a segment enters a bad state and when the alert fires.

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Symptoms

### Alert Expression

```promql
sum by (org_id, kube_cluster_name, kf_node, table) (
  pinot_controller_segmentsInErrorState_Value{
    kfuse="true",
    kube_service="pinot-controller",
    table=~"kf_logs|kf_metrics|kf_metrics_rollup"
  } > 0
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

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `pinot_controller_segmentsInErrorState_Value` | `0` | `> 0` |
| `pinot_controller_percentSegmentsAvailable_Value` | `100` | `< 100` |
| `pinot_controller_validation_missingSegmentCount_Value` | `0` | `> 0` |

---

## Step 1: Identify the Affected Node and Table

The alert label `kf_node` identifies the Pinot controller node reporting the error, and `table` identifies the affected table. Note the table name from the alert — it will be used throughout this runbook.

Verify the Pinot pods on the affected node are running:

```bash
kubectl get pods -n kfuse -o wide | grep pinot | grep <NODE_NAME>
```

Check the overall health of all Pinot pods:

```bash
kubectl get pods -n kfuse | grep pinot
```

Expected output — all pods should show `Running`:

```
pinot-broker-0        1/1     Running   0          2d
pinot-controller-0    1/1     Running   0          2d
pinot-server-0        1/1     Running   0          2d
pinot-server-1        1/1     Running   0          2d
pinot-server-2        1/1     Running   0          2d
```

If any pod is not Running, address pod health first:

- For `CrashLoopBackOff` → see the [CrashLoopBackOff runbook](crashloopbackupoff_alert.md)
- For `ImagePullBackOff` → see the [ImagePullBackOff runbook](imagepullbackoff_alert.md)

---

## Step 2: Identify Segments in ERROR State

Use the [segments-error.sh](../../scripts/alerts/segments-error.sh) script to list ERROR segments and their server assignments for the affected table from the alert:

```bash
# Show segment states for the affected table
./segments-error.sh status <TABLE_NAME>

# Show segment states and server assignments side-by-side
./segments-error.sh diagnose <TABLE_NAME>
```

---

## Step 3: Check Pinot Server Logs

Search Kloudfuse logs for errors on the affected server around the time the alert fired.

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

Set the time range to cover when the alert fired, then run:

```
kube_pod*~"pinot-server" and kf_node="<NODE_NAME>" and (__kf_level="ERROR" or __kf_level="WARN")
```

To narrow to segment-specific failures:

```
kube_pod*~"pinot-server" and kf_node="<NODE_NAME>" and ("Failed to load" or "Failed to download" or "segment" or "ERROR")
```

Common error patterns:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `Failed to download segment` | Deep store connectivity or permissions issue |
| `Segment not found in deep store` | Segment missing or corrupted in deep store |
| `Failed to load segment` | Local disk issue or segment corruption |
| `OutOfMemoryError` | Server OOM — needs resource increase |
| `No space left on device` | Server disk full |

---

## Step 4: Diagnose Root Cause

### Case A: Server Was Recently Restarted

After a server restart, Pinot must re-download segments from deep store. During this time segments may temporarily appear in ERROR before transitioning to ONLINE.

Check if segments are actively loading:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod*~"pinot-server" and kf_node="<NODE_NAME>" and ("Downloading" or "Loading segment" or "Loaded segment")
```

If you see a steady stream of `Loaded segment` messages, the server is recovering — wait for it to complete and monitor:

```bash
CONTROLLER_POD=$(kubectl get pods -n kfuse -l app=pinot-controller -o jsonpath='{.items[0].metadata.name}')
TABLE_NAME="<TABLE_NAME>"

watch -n 30 "kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s \"http://localhost:9000/tables/${TABLE_NAME}/segments\" | \
  python3 -c \"import sys,json; data=json.load(sys.stdin); print(data)\""
```

Or use the script:

```bash
./segments-error.sh status <TABLE_NAME>
```

### Case B: Deep Store Connectivity Issue

Search for download errors:

```
kube_pod*~"pinot-server" and kf_node="<NODE_NAME>" and ("Failed to download" or "Access Denied" or "NoSuchKey" or "403" or "404")
```

- `Access Denied` / `403` → check IAM role or service account permissions for the Pinot server
- `NoSuchKey` / `404` → segment may be missing from deep store — proceed to **Case D**

**Resolution:** Fix credentials or network connectivity, then trigger a segment reload (see Step 5).

### Case C: Server Disk Full

Check disk usage on the affected node:

```bash
kubectl debug node/<NODE_NAME> -it --image=ubuntu -- df -h
```

If the server's data directory is full:

```bash
# Check disk usage inside the pinot-server pod
kubectl exec -n kfuse <SERVER_POD> -- df -h /var/pinot
```

**Resolution:** Free up disk space or expand the PVC, then restart the server pod to allow segment reload:

```bash
kubectl delete pod -n kfuse <SERVER_POD>
kubectl wait --for=condition=Ready pod/<SERVER_POD> -n kfuse --timeout=600s
```

### Case D: Segment Corrupted or Missing from Deep Store

If a segment is confirmed missing from deep store:

- For **OFFLINE** tables: the data for that time range may be lost unless a backup exists
- For **REALTIME** tables: if Kafka retention covers the missing segment's time range, the segment can be rebuilt by resetting the consuming offset (see Step 6)

Check if the segment exists in deep store (replace with your configuration):

```bash
# For S3 deep store
aws s3 ls s3://<BUCKET>/pinot/<TABLE_NAME>/<SEGMENT_NAME>/

# For GCS deep store
gsutil ls gs://<BUCKET>/pinot/<TABLE_NAME>/<SEGMENT_NAME>/
```

---

## Step 5: Reload Segments

Once the underlying cause is resolved, trigger a segment reload. The script will automatically re-check segment states after the reload:

```bash
# Reload all segments for a table
./segments-error.sh reload <TABLE_NAME>

# Reload a single segment
./segments-error.sh reload <TABLE_NAME> <SEGMENT_NAME>
```

---

## Step 6: Reset REALTIME Segment Consumption (If Kafka Data Is Available)

If a REALTIME segment is stuck in ERROR and Kafka still has the data, reset the consuming segment to restart ingestion.

> **Warning:** Only use this for REALTIME tables. Confirm with your team before proceeding — incorrect resets can cause data duplication or loss.

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
pinot_controller_segmentsInErrorState_Value{
  kfuse="true",
  table=~"kf_logs|kf_metrics|kf_metrics_rollup"
} > 0
```

### Monitor Server Restarts

Frequent server restarts cause repeated segment reload delays that can temporarily put segments into ERROR:

```promql
increase(kube_pod_container_status_restarts_total{namespace="kfuse", pod=~"pinot-server.*"}[1h]) > 2
```

### Ensure Adequate Server Resources

Prevent OOM-related segment failures by tuning the server heap size. Use `jvmMemory` in `values.yaml` — specify an integer followed by `G`:

```yaml
server:
  jvmMemory: 8G
```

`jvmMemory` sets both `-Xms` and `-Xmx` to the specified value. Only use `jvmOpts` if you need full control over individual JVM flags.

### Ensure Adequate Disk Space

Monitor disk usage on Pinot server nodes and expand PVCs proactively before they reach capacity.

---

## Related Runbooks

- [Pinot Segments Unavailable](pinot-segments-unavailable.md) — Broader segment availability issues including transient unavailability
- [Pinot ZooKeeper Corruption Recovery](pinot-zookeeper-corruption-recovery.md) — ZooKeeper quorum loss affecting Pinot state
- [Node condition not Ready](node_status.md) — Node-level failures that may suppress this alert
- [CrashLoopBackOff Alert](crashloopbackupoff_alert.md) — Pod crash-looping
- [Pod Failed Alert](pod_failed_alert.md) — Pod in Failed state
