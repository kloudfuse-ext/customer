# Pinot ZooKeeper Data Corruption Recovery

## Summary

When a Pinot ZooKeeper node experiences data corruption (typically due to OOM killing the SyncThread mid-write), it enters a crash loop and cannot rejoin the ensemble. This runbook provides steps to identify the corrupted node and recover it by clearing the corrupted data.

**Impact:** The corrupted node cannot participate in the ZooKeeper quorum. If only one node is affected and 2 of 3 nodes remain healthy, the cluster maintains quorum but is at risk - one more failure will cause complete Pinot outage.

**Root Cause:** Java OutOfMemoryError on the ZooKeeper leader kills the SyncThread responsible for writing transaction logs, causing incomplete writes and epoch/zxid mismatch.

---

## Symptoms

### Log Messages Indicating Corruption

```
java.io.IOException: The current epoch, b8, is older than the last zxid, 794568949761
    at org.apache.zookeeper.server.quorum.QuorumPeer.loadDataBase(QuorumPeer.java:1178)
```

```
ERROR - Committed proposal cached out of order: 0x403000001b3 is not the next proposal of 0x4030000018d
```

```
WARN  - Digests are not matching. Value is Zxid.
INFO  - Peer state changed: looking - trunc
INFO  - LOOKING
```

### Metrics Indicating Issue

The `zookeeper_synced_followers` metric on the leader will show fewer followers than expected:
- For a 3-node cluster: should be `2`, will show `1` if one node is corrupted
- For a 5-node cluster: should be `4`, will show `3` if one node is corrupted

---

## Alert Expression

Use this PromQL expression to alert on ZooKeeper cluster health issues:

```promql
(
  max by (org_id, kube_cluster_name) (zookeeper_synced_followers)
  <
  (max by (org_id, kube_cluster_name) (zookeeper_quorum_size) - 1)
)
or
(
  count by (org_id, kube_cluster_name) (zookeeper_uptime)
  <
  max by (org_id, kube_cluster_name) (zookeeper_quorum_size)
)
```

---

## Pre-Recovery Checks

### Step 1: Verify Cluster Has Quorum

Before proceeding, confirm at least 2 of 3 nodes (or majority) are healthy:

```bash
# Check which node is the leader
kubectl exec -n kfuse pinot-zookeeper-0 -- zkServer.sh status
kubectl exec -n kfuse pinot-zookeeper-1 -- zkServer.sh status
kubectl exec -n kfuse pinot-zookeeper-2 -- zkServer.sh status
```

You should see one node reporting `Mode: leader` and at least one reporting `Mode: follower`.

### Step 2: Identify the Corrupted Node

Check logs for corruption errors:

```bash
# Check each node for corruption errors
for i in 0 1 2; do
  echo "=== pinot-zookeeper-$i ==="
  kubectl logs -n kfuse pinot-zookeeper-$i --tail=50 2>/dev/null | grep -E "epoch|zxid|LOOKING|out of order|IOException"
done
```

The corrupted node will show errors like:
- `The current epoch ... is older than the last zxid`
- `Committed proposal cached out of order`
- Repeatedly showing `LOOKING` state

### Step 3: Verify Synced Followers Count

On the leader node, check synced followers:

```bash
# Replace X with the leader node number
kubectl exec -n kfuse pinot-zookeeper-X -- bash -c 'echo "mntr" | nc localhost 2181 | grep synced_followers'
```

For a healthy 3-node cluster, this should show `zk_synced_followers 2`.

---

## Recovery Procedure

### Step 1: Confirm the Target Node

Double-check you have identified the correct corrupted node. **Do not run these commands on a healthy node.**

```bash
# Example: if pinot-zookeeper-0 is corrupted
NODE=0
kubectl logs -n kfuse pinot-zookeeper-${NODE} --tail=20 | grep -E "LOOKING|epoch|zxid"
```

### Step 2: Delete Corrupted Transaction Logs

```bash
# Delete the version-2 directory contents (transaction logs and snapshots)
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- rm -rf /bitnami/zookeeper/data/version-2
```

### Step 3: Restart the Pod

```bash
# Delete the pod to force restart with clean state
kubectl delete pod -n kfuse pinot-zookeeper-${NODE}
```

### Step 4: Wait for Pod Recovery

```bash
# Wait for pod to be ready (timeout 5 minutes)
kubectl wait --for=condition=Ready pod/pinot-zookeeper-${NODE} -n kfuse --timeout=300s
```

### Step 5: Verify Node Rejoined as Follower

```bash
# Check the node status
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- zkServer.sh status
```

Should show `Mode: follower`.

### Step 6: Verify Synced Followers Restored

On the leader node:

```bash
kubectl exec -n kfuse pinot-zookeeper-X -- bash -c 'echo "mntr" | nc localhost 2181 | grep synced_followers'
```

Should now show `zk_synced_followers 2` for a 3-node cluster.

---

## Alternative: Full Data Wipe

If the standard recovery doesn't work, perform a complete data wipe:

```bash
NODE=0  # Set to the corrupted node number

# Delete all ZK data
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- rm -rf /bitnami/zookeeper/data/*

# Also clear the datalog directory if separate
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- rm -rf /bitnami/zookeeper/datalog/* 2>/dev/null || true

# Delete the pod
kubectl delete pod -n kfuse pinot-zookeeper-${NODE}

# Wait for recovery
kubectl wait --for=condition=Ready pod/pinot-zookeeper-${NODE} -n kfuse --timeout=300s
```

---

## Post-Recovery Verification

### Verify All Nodes Healthy

```bash
# Check all nodes
for i in 0 1 2; do
  echo "=== pinot-zookeeper-$i ==="
  kubectl exec -n kfuse pinot-zookeeper-$i -- zkServer.sh status
done
```

### Verify Metrics

Check these Prometheus queries:

```promql
# Should return 3 for a 3-node cluster
count by (org_id) (zookeeper_uptime{org_id="YOUR_ORG_ID"})

# Leader should report 2 for a 3-node cluster
zookeeper_synced_followers{org_id="YOUR_ORG_ID"}
```

### Verify Pinot Services

```bash
kubectl get pods -n kfuse | grep pinot
```

All Pinot pods (controller, broker, server) should be Running.

---

## Prevention

### Monitor ZooKeeper Heap Usage

The corruption is typically caused by OOM. Monitor JVM heap usage:

```promql
jvm_memory_bytes_used{area="heap", pod=~"pinot-zookeeper.*"} /
jvm_memory_bytes_max{area="heap", pod=~"pinot-zookeeper.*"}
```

### Increase ZooKeeper Heap Size

If heap usage is consistently high (>80%), increase `ZOO_HEAP_SIZE` in values.yaml:

```yaml
pinot:
  zookeeper:
    env:
      ZOO_HEAP_SIZE: 2048  # Increase from default 1024 (MB)
```

### Recommended Alert

Add an alert for ZooKeeper heap pressure:

```promql
(
  jvm_memory_bytes_used{area="heap", pod=~"pinot-zookeeper.*"}
  /
  jvm_memory_bytes_max{area="heap", pod=~"pinot-zookeeper.*"}
) > 0.85
```

---

## Important Notes

- **No data loss from recovery**: The healthy nodes have the complete ZooKeeper state. The recovered node will sync from them.
- **Pinot continues operating**: As long as quorum (2 of 3 nodes) is maintained, Pinot services remain available during recovery.
- **Timing**: Recovery can be done anytime but is best during low-traffic periods as a precaution.
- **Do not delete data on healthy nodes**: Only clear data on the corrupted node. Clearing a healthy node's data could cause data loss.

---

## Related Incidents

- **Dec 18, 2025 - AA Pinot ZooKeeper Corruption**: OOM on pinot-zookeeper-1 killed SyncThread, causing epoch/zxid mismatch. Resolved by deleting corrupted data and restarting pod. 3-4 hours of data loss due to Kafka retention during outage.
