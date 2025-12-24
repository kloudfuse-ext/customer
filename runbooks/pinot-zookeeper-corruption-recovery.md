# Pinot ZooKeeper Data Corruption Recovery

## Summary

When a Pinot ZooKeeper node experiences data corruption (typically due to OOM killing the SyncThread mid-write), it enters a crash loop and cannot rejoin the ensemble. This runbook provides steps to identify the corrupted node and recover it by clearing the corrupted data.

**Impact:** The corrupted node cannot participate in the ZooKeeper quorum. If only one node is affected and 2 of 3 nodes remain healthy, the cluster maintains quorum but is at risk - one more failure will cause complete Pinot outage.

**Root Cause:** Java OutOfMemoryError on the ZooKeeper leader kills the SyncThread, which is responsible for writing transaction logs, causing incomplete writes and an epoch/zxid mismatch.

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

**Note:** This runbook is designed for standard 3-node ZooKeeper clusters. For larger clusters (e.g., 5-node), adjust the NODE validation range accordingly.

---

## Symptoms

### Log Messages Indicating Corruption

```
java.io.IOException: The current epoch, b8, is older than the last zxid, 0xb9003a0001
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

Before proceeding, confirm at least 2 of 3 nodes (or majority) are healthy. Use the ZooKeeper 4-letter command `srvr` to check status:

```bash
# Check status of each node using the 4-letter 'srvr' command
for i in 0 1 2; do
  echo "=== pinot-zookeeper-$i ==="
  kubectl exec -n kfuse pinot-zookeeper-$i -- bash -c 'echo "srvr" | nc localhost 2181' 2>/dev/null | grep -E "Mode|Zxid"
done
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

### Step 3: Find the Leader Node and Verify Synced Followers

Dynamically determine which node is the leader:

```bash
# Find the leader node
LEADER=""
for i in 0 1 2; do
  MODE=$(kubectl exec -n kfuse pinot-zookeeper-$i -- bash -c 'echo "srvr" | nc localhost 2181' 2>/dev/null | grep "Mode:" | awk '{print $2}')
  echo "pinot-zookeeper-$i: $MODE"
  if [[ "$MODE" == "leader" ]]; then
    LEADER=$i
    break
  fi
done

if [[ -z "$LEADER" ]]; then
  echo "ERROR: Could not determine leader node. Check ZooKeeper status manually."
  exit 1
fi
echo "Leader is pinot-zookeeper-$LEADER"
```

Then verify synced followers on the leader:

```bash
# Check synced followers on the leader (use the LEADER value from above)
kubectl exec -n kfuse pinot-zookeeper-"$LEADER" -- bash -c 'echo "mntr" | nc localhost 2181 | grep synced_followers'
```

For a healthy 3-node cluster, this should show `zk_synced_followers 2`.

---

## Recovery Procedure

### Step 1: Confirm the Target Node

Double-check you have identified the correct corrupted node. **Do not run these commands on a healthy node.**

```bash
# Set NODE to the corrupted node number (e.g., 0, 1, or 2 for a 3-node cluster)
NODE=0

# Validate NODE is set
if [[ -z "${NODE:-}" ]]; then
  echo "ERROR: NODE is not set. Please set NODE to the corrupted node number (e.g., 0, 1, 2)."
  exit 1
fi

# Validate NODE is within the expected range for a 3-node cluster
# For larger clusters, adjust the regex pattern (e.g., ^[0-4]$ for 5-node)
if [[ ! "$NODE" =~ ^[0-2]$ ]]; then
  echo "ERROR: NODE must be 0, 1, or 2 for a 3-node cluster. Current value: $NODE"
  exit 1
fi

# Verify the pod exists
if ! kubectl get pod -n kfuse "pinot-zookeeper-${NODE}" >/dev/null 2>&1; then
  echo "ERROR: Pod 'pinot-zookeeper-${NODE}' not found in namespace 'kfuse'."
  exit 1
fi

kubectl logs -n kfuse pinot-zookeeper-${NODE} --tail=20 | grep -E "LOOKING|epoch|zxid"
```

**STOP: Before proceeding, verify you see corruption errors in the output above.**

You MUST see at least one of these error patterns:
- `The current epoch ... is older than the last zxid`
- `Committed proposal cached out of order`
- `LOOKING` state appearing repeatedly

If you do NOT see these errors, DO NOT proceed - you may have identified the wrong node.

### Step 2: Delete Corrupted Transaction Logs

Only proceed after confirming corruption errors in Step 1. Document which NODE you are working on and have a second engineer review and confirm before running any destructive commands below (especially in production).

```bash
# Confirm before destructive operation
echo "About to delete transaction logs on pod: pinot-zookeeper-${NODE}"
read -r -p "Type 'YES' to confirm: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
  echo "Aborted by user."
  exit 1
fi

# Delete the version-2 directory contents (transaction logs and snapshots)
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- bash -c 'if [ -d /bitnami/zookeeper/data/version-2 ]; then rm -rf /bitnami/zookeeper/data/version-2; fi'
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
# Check the node status using 4-letter command
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- bash -c 'echo "srvr" | nc localhost 2181 | grep Mode'
```

Should show `Mode: follower`.

### Step 6: Verify Synced Followers Restored

Find the leader and verify synced followers:

> **Note:** The leader-finding logic below is intentionally duplicated from Pre-Recovery Checks Step 3 to allow each section to be executed independently. For frequent use, consider creating a reusable shell function or script.

```bash
# Find the leader node
LEADER=""
for i in 0 1 2; do
  MODE=$(kubectl exec -n kfuse pinot-zookeeper-$i -- bash -c 'echo "srvr" | nc localhost 2181' 2>/dev/null | grep "Mode:" | awk '{print $2}')
  if [[ "$MODE" == "leader" ]]; then
    LEADER=$i
    break
  fi
done

if [[ -z "$LEADER" ]]; then
  echo "ERROR: No ZooKeeper leader found; cannot check synced followers."
  exit 1
fi

# Check synced followers
kubectl exec -n kfuse pinot-zookeeper-"$LEADER" -- bash -c 'echo "mntr" | nc localhost 2181 | grep synced_followers'
```

Should now show `zk_synced_followers 2` for a 3-node cluster.

---

## Alternative: Full Data Wipe

If the standard recovery doesn't work, perform a complete data wipe:

```bash
NODE=0  # Set to the corrupted node number

# Validate NODE before running destructive commands
if [[ -z "${NODE:-}" ]]; then
  echo "ERROR: NODE is not set. Please set NODE to the corrupted node number (e.g., 0, 1, 2)."
  exit 1
fi

# Ensure NODE is a valid integer for a 3-node cluster
# For larger clusters, adjust the regex pattern (e.g., ^[0-4]$ for 5-node)
if [[ ! "$NODE" =~ ^[0-2]$ ]]; then
  echo "ERROR: NODE must be 0, 1, or 2 for a 3-node cluster. Current value: $NODE"
  exit 1
fi

# Verify that the target pod exists
if ! kubectl get pod -n kfuse "pinot-zookeeper-${NODE}" >/dev/null 2>&1; then
  echo "ERROR: Pod 'pinot-zookeeper-${NODE}' not found in namespace 'kfuse'."
  exit 1
fi

# Check for corruption errors before proceeding
echo "=== Checking for corruption errors on pinot-zookeeper-${NODE} ==="
kubectl logs -n kfuse pinot-zookeeper-${NODE} --tail=20 | grep -E "LOOKING|epoch|zxid"

echo ""
echo "STOP: Before proceeding, verify you see corruption errors in the output above."
echo "You MUST see at least one of: 'epoch ... zxid', 'out of order', or repeated 'LOOKING' state."
echo "If you do NOT see these errors, DO NOT proceed - you may have identified the wrong node."
echo ""

echo "About to perform a FULL DATA WIPE on pod: pinot-zookeeper-${NODE} (namespace: kfuse)."
echo "This will delete all ZooKeeper data and the pod itself."
read -r -p "Type 'YES' to confirm and continue: " CONFIRM
if [[ "$CONFIRM" != "YES" ]]; then
  echo "Aborted by user."
  exit 1
fi

# Delete all ZK data (with existence check)
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- bash -c 'if [ -d /bitnami/zookeeper/data ]; then rm -rf /bitnami/zookeeper/data/*; fi'

# Also clear the datalog directory if it exists
kubectl exec -n kfuse pinot-zookeeper-${NODE} -- bash -c 'if [ -d /bitnami/zookeeper/datalog ]; then rm -rf /bitnami/zookeeper/datalog/*; fi'

# Delete the pod
kubectl delete pod -n kfuse pinot-zookeeper-${NODE}

# Wait for recovery
kubectl wait --for=condition=Ready pod/pinot-zookeeper-${NODE} -n kfuse --timeout=300s
```

---

## Post-Recovery Verification

### Verify All Nodes Healthy

```bash
# Check all nodes using 4-letter command
for i in 0 1 2; do
  echo "=== pinot-zookeeper-$i ==="
  kubectl exec -n kfuse pinot-zookeeper-$i -- bash -c 'echo "srvr" | nc localhost 2181' 2>/dev/null | grep -E "Mode|Zxid"
done
```

### Verify Metrics

Check these Prometheus queries. Replace the placeholder values with your actual values:
- `YOUR_ORG_ID`: Your organization ID (e.g., `acme-production`, `acme-staging`)
- `YOUR_CLUSTER_NAME`: Your Kubernetes cluster name (e.g., `production-us-west-2`, `staging-us-east-1`)

```promql
# Should return 3 for a 3-node cluster
count by (org_id, kube_cluster_name) (zookeeper_uptime{org_id="YOUR_ORG_ID", kube_cluster_name="YOUR_CLUSTER_NAME"})

# Leader should report 2 for a 3-node cluster
zookeeper_synced_followers{org_id="YOUR_ORG_ID", kube_cluster_name="YOUR_CLUSTER_NAME"}
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

- **No ZooKeeper state loss from recovery**: The healthy nodes have the complete ZooKeeper state. The recovered node will sync from them. However, during an extended outage where Pinot cannot ingest data, Kafka topic retention may expire causing Pinot data loss (see Related Incidents).
- **Pinot continues operating**: As long as quorum (2 of 3 nodes) is maintained, Pinot services remain available during recovery.
- **Timing**: Recovery can be done anytime but is best during low-traffic periods as a precaution.
- **Do not delete data on healthy nodes**: Only clear data on the corrupted node. Clearing a healthy node's data could cause data loss.

---

## Related Incidents

- **Dec 18, 2025 - AA Pinot ZooKeeper Corruption**: OOM on pinot-zookeeper-1 killed SyncThread, causing epoch/zxid mismatch. Resolved by deleting corrupted data and restarting pod. Note: While ZooKeeper state recovery itself has no data loss, the extended outage (~3-4 hours) meant Pinot could not ingest data during that time, and Kafka topic retention expired for backlog messages, resulting in permanent Pinot data loss for that window.
