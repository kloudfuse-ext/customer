# Pinot Segments Unavailable

## Summary

When Apache Pinot segments are reported as unavailable, queries against those tables will return partial results or fail with "No server found for segment" errors. This runbook provides steps to identify the root cause and restore segment availability.

**Impact:** Queries against affected tables return incomplete or no data. Real-time ingestion may also be impacted if consuming segments are affected.

**Common Root Causes:**
- Pinot server pod is down or crash-looping
- Server restarted and segments have not finished reloading from deep store
- Deep store (S3/GCS/Azure Blob) connectivity issues preventing segment download
- Segment corruption in deep store or on the server
- ZooKeeper state mismatch — controller believes a segment is assigned to a server that can't serve it

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
| `pinot_controller_numSegmentsWithError` | `0` | `> 0` |
| `pinot_server_numSegmentsWithErrors` | `0` | `> 0` |
| `pinot_broker_numUnavailableSegments` | `0` | `> 0` |

### Alert Expression

```promql
pinot_controller_numSegmentsWithError{org_id="<ORG_ID>"} > 0
```

Or for broker-reported unavailable segments:

```promql
pinot_broker_numUnavailableSegments{org_id="<ORG_ID>"} > 0
```

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

## Step 2: Identify Affected Tables and Segments

Use the Pinot Controller REST API to find which segments are in an error state.

### Get Controller Pod Name

```bash
CONTROLLER_POD=$(kubectl get pods -n kfuse -l app=pinot-controller -o jsonpath='{.items[0].metadata.name}')
echo "Controller pod: $CONTROLLER_POD"
```

### List All Tables

```bash
kubectl exec -n kfuse $CONTROLLER_POD -- curl -s http://localhost:9000/tables | python3 -m json.tool
```

### Check Segment Metadata for a Specific Table

Replace `<TABLE_NAME>` with the table name (e.g., `logs_REALTIME` or `traces_OFFLINE`):

```bash
TABLE_NAME="<TABLE_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/${TABLE_NAME}/segments" | python3 -m json.tool
```

### Find Segments in ERROR State

```bash
TABLE_NAME="<TABLE_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/${TABLE_NAME}/segments?includeReplacedSegments=false" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        if state != 'ONLINE':
            print(f'{state}: {seg}')
"
```

### Check Segment Assignment (Which Server Hosts Each Segment)

```bash
TABLE_NAME="<TABLE_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/${TABLE_NAME}/externalview" | python3 -m json.tool
```

Look for segments where state is `ERROR` or `OFFLINE` instead of `ONLINE`.

---

## Step 3: Check Pinot Server Logs

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

## Step 4: Diagnose Root Cause

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
watch -n 30 'kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/<TABLE_NAME>/segments" | \
  python3 -c "import sys,json; data=json.load(sys.stdin); print(data)"'
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
```

If the segment is confirmed missing or corrupted:

- For **OFFLINE** tables: the data for that time range is lost unless a backup exists.
- For **REALTIME** tables: if Kafka retention covers the missing segment's time range, the segment can be rebuilt by resetting the segment consumption offset (see Step 6).

---

## Step 5: Reload Segments

If segments are in ERROR state and the underlying cause (connectivity, server health) is resolved, trigger a reload.

### Reload a Single Segment

```bash
TABLE_NAME="<TABLE_NAME>"
SEGMENT_NAME="<SEGMENT_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s -X POST "http://localhost:9000/tables/${TABLE_NAME}/segments/${SEGMENT_NAME}/reload" \
  | python3 -m json.tool
```

### Reload All Segments for a Table

```bash
TABLE_NAME="<TABLE_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s -X POST "http://localhost:9000/tables/${TABLE_NAME}/segments/reload" \
  | python3 -m json.tool
```

After triggering a reload, monitor the segment states until all return to `ONLINE`:

```bash
TABLE_NAME="<TABLE_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/${TABLE_NAME}/segments" | python3 -m json.tool
```

---

## Step 6: Reset REALTIME Segment Consumption (If Kafka Data Is Available)

If a REALTIME segment is stuck in ERROR and Kafka still has the data, reset the consuming segment to restart ingestion from the correct offset.

> **Warning:** Only use this for REALTIME tables. Resetting a consuming segment that has already been committed may cause data duplication or loss if done incorrectly. Confirm with your team before proceeding.

### Find Consuming Segments in ERROR

```bash
TABLE_NAME="<TABLE_NAME>_REALTIME"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/${TABLE_NAME}/segments" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        if state == 'ERROR':
            print(seg)
"
```

### Reset the Segment

```bash
TABLE_NAME="<TABLE_NAME>_REALTIME"
SEGMENT_NAME="<SEGMENT_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s -X POST "http://localhost:9000/segments/${TABLE_NAME}/${SEGMENT_NAME}/reset" \
  | python3 -m json.tool
```

Monitor the Pinot server logs after reset to confirm the segment resumes consumption:

```bash
kubectl logs -n kfuse <SERVER_POD> -f | grep -E "${SEGMENT_NAME}|Consuming|CONSUMING"
```

---

## Step 7: Post-Recovery Verification

### Verify All Segments Are ONLINE

```bash
TABLE_NAME="<TABLE_NAME>"

kubectl exec -n kfuse $CONTROLLER_POD -- \
  curl -s "http://localhost:9000/tables/${TABLE_NAME}/segments" \
  | python3 -c "
import sys, json
data = json.load(sys.stdin)
total, online, other = 0, 0, []
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        total += 1
        if state == 'ONLINE':
            online += 1
        else:
            other.append((seg, state))
print(f'Total: {total}, ONLINE: {online}, Other: {len(other)}')
for seg, state in other:
    print(f'  {state}: {seg}')
"
```

### Verify Metrics Are Healthy

Replace the placeholder values with your actual values:
- `<ORG_ID>`: Your organization ID
- `<KUBE_CLUSTER_NAME>`: Your Kubernetes cluster name

```promql
# Should be 0
pinot_controller_numSegmentsWithError{org_id="<ORG_ID>", kube_cluster_name="<KUBE_CLUSTER_NAME>"}

# Should be 0
pinot_broker_numUnavailableSegments{org_id="<ORG_ID>", kube_cluster_name="<KUBE_CLUSTER_NAME>"}
```

### Verify Query Returns Data

Run a test query against the affected table through the Pinot broker:

```bash
BROKER_POD=$(kubectl get pods -n kfuse -l app=pinot-broker -o jsonpath='{.items[0].metadata.name}')
TABLE_NAME="<TABLE_NAME>"

kubectl exec -n kfuse $BROKER_POD -- \
  curl -s -X POST "http://localhost:8099/query/sql" \
  -H "Content-Type: application/json" \
  -d "{\"sql\": \"SELECT COUNT(*) FROM ${TABLE_NAME} LIMIT 1\"}" \
  | python3 -m json.tool
```

A healthy response will include `"numServersQueried"` matching `"numServersResponded"` with no exceptions.

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

Segment load failures from OOM are prevented by tuning server heap size in values.yaml:

```yaml
pinot:
  server:
    jvmOpts: "-Xms4G -Xmx8G"
```

### Replication Factor

Ensure tables have a replication factor of at least 2 (ideally 3) so that a single server failure does not make segments unavailable:

```json
{
  "tableName": "<TABLE_NAME>",
  "replication": "3"
}
```

---

## Related Runbooks

- [Pinot ZooKeeper Corruption Recovery](pinot-zookeeper-corruption-recovery.md) — ZooKeeper quorum loss affecting Pinot state
- [CrashLoopBackOff Alert](crashloopbackupoff_alert.md) — Pod crash-looping
- [Pod Failed Alert](pod_failed_alert.md) — Pod in Failed state
