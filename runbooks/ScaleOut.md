# Scale Out Kloudfuse

## Table of Contents

- [When to scale out](#when-to-scale-out)
  - [User Visible Impact](#user-visible-impact)
  - [Internal Impact](#internal-impact)
  - [Preparation](#preparation)
  - [IOPS Considerations During Scale Out](#iops-considerations-during-scale-out)
  - [Execution](#execution)
- [Validation](#validation)
- [Troubleshooting: Pinot Segments Unavailable After Scale Out](#troubleshooting-pinot-segments-unavailable-after-scale-out)
  - [Symptom](#symptom)
  - [Root Cause](#root-cause)
  - [Diagnosis](#diagnosis)
  - [Recovery](#recovery)
  - [Prevention](#prevention)
- [Troubleshooting: Pinot REALTIME Segments Stuck Due to S3 Upload Timeout](#troubleshooting-pinot-realtime-segments-stuck-due-to-s3-upload-timeout)
  - [Symptom](#symptom-1)
  - [Root Cause](#root-cause-1)
  - [Recovery](#recovery-1)
  - [When Pod Restart Is Not Enough](#when-pod-restart-is-not-enough)

---

To handle increased volume of data, kloudfuse stack can be scaled out by adding additional kubernetes nodes. This runbook describes how to add additional capacity for running kloudfuse stack through addition of new nodes.

## When to scale out
Sudden increase in the incoming volume of logs, metrics, traces, RUM, etc. will impact the kloudfuse stack in the following way:
### User Visible Impact
* Lagging of data as seen from the UI - older data is visible; more recent data is not visible
* Alert rule status seen as “No Data”
* UI showing various query failure error messages
### Internal Impact
* Increased CPU, memory and disk consumption used by the kloudfuse services and pods
* Crashing of various kloudfuse pods (ingester, kafka, etc.)
* Increased consumer lag in logs, metrics, APM kafka topics.
If the incoming volume increase is temporary, the user visible impact will be temporary and kloudfuse cluster will recover on its own.
If the incoming volume increase is longer term (or permanent), kloudfuse cluster will need to be scaled.

Executing this runbook requires additional investigation; therefore, this runbook should not be executed without involvement of the kloudfuse support.

To add additional nodes follow the steps below:
### Preparation
- [ ] Review and validate if the existing customer values yaml file is correctly configured and up-to-date wrt actual kloudfuse installation. This is important if are changes made directly on the kloudfuse cluster that are not reflected in the customer values yaml. For example, if PVC is resized on the kloudfuse cluster, values yaml file might not have been updated.
- [ ] Adjust the customer values yaml file by:
    * increasing the replica for each of the services by the right amount.
        * for zookeeper (kafka zookeeper and pinot zookeeper) keep the number of replicas to 3.
        * for some services such as, kfuse-redis, kfuse-configdb, kfuse-grafana, etc. keep the number of replicas at 1 as these services do not need to be scaled.
        * for all other services increase the number of replicas by appropriate ratio. So, if there were n nodes and m new nodes are being added, the replicas should be scaled up `(n + m) / n` factor.
    * Increase the number of partitions based on the increased volume as well as expected increase in the volume. Each of the streams such as, logs, metrics, APM have their specific topics for ingest, tranformers as well as for pinot. They all need to be increased in the right proportion.
    * Get the customer value yaml file reviewed by the CS as well as engineering team.
    
### IOPS Considerations During Scale Out

During a scale out, Pinot servers experience a surge in disk I/O as they:
- Download segments from S3/GCS to new server nodes (segment rebalancing)
- Simultaneously commit new REALTIME segments to S3/GCS as Kafka consumption continues
- Rebuild Lucene text indexes for log tables

If the EBS volumes provisioned for Pinot servers are on gp2 or have insufficient provisioned IOPS, this combined read + write load can saturate the disk throughput. When disk I/O is saturated:
- S3 uploads of newly committed REALTIME segments will time out and fail
- Pinot retries these uploads a limited number of times and then **stops retrying entirely**, leaving segments permanently stuck in an uncommitted (UPDATING) state
- `percentSegmentsAvailable` drops and stays low — the cluster will not self-heal without intervention

**Before starting the scale out**, check the current IOPS configuration for Pinot server nodes:

```bash
# Check the storage class and volume type used by pinot-server PVCs
kubectl get pvc -n kfuse | grep pinot-server
kubectl get pvc -n kfuse <PVC_NAME> -o jsonpath=’{.spec.storageClassName}’
kubectl get storageclass <STORAGE_CLASS_NAME> -o yaml
```

For AWS deployments, upgrade Pinot server EBS volumes from `gp2` to `gp3` and set provisioned IOPS to at least **6000 IOPS** (and throughput to **500 MB/s**) before executing the scale out. This can be done without downtime via an AWS console or CLI volume modification:

```bash
# Find the EBS volume IDs backing pinot-server PVCs
kubectl get pv $(kubectl get pvc -n kfuse -l app=pinot,component=server \
  -o jsonpath=’{.items[*].spec.volumeName}’) \
  -o jsonpath=’{range .items[*]}{.metadata.name}{"\t"}{.spec.awsElasticBlockStore.volumeID}{"\n"}{end}’

# Modify each volume to gp3 with provisioned IOPS (replace <VOL_ID>)
aws ec2 modify-volume --volume-id <VOL_ID> \
  --volume-type gp3 --iops 6000 --throughput 500
```

For GCP deployments, ensure the Pinot server persistent disks are `pd-ssd` type and consider using `hyperdisk-throughput` volumes for heavy I/O workloads.

After the scale out is complete and segment rebalancing has finished, you can reduce provisioned IOPS back to normal steady-state levels if cost is a concern.

### Execution
- [ ] **Increase IOPS before starting** — upgrade Pinot server EBS volumes to gp3 with ≥6000 IOPS as described above.
- [ ] Increase the capacity of the AWS or GCP node pool with additional nodes. It is better to expand existing node pool instead of creating new one as kloudfuse installation requires all nodes to be of the same type and using the same set of taints and labels.
- [ ] Once the new kubernetes node addition is complete and nodes are ready to run pods, do the helm upgrade using the updated customer values yaml using the same version as currently installed. This is to avoid accidentally doing software upgrade in addition to scaling the kloudfuse cluster.
- [ ] Verify that all pods and services are up and running and evenly distributed among the old and the new nodes. You can use the control plane’s overview page to confirm that kloudfuse stack is running fine.
- [ ] Because we added additional partitions to existing topics, we need to do [kafka rebalance](kafka-rebalance.md) so that new kafka brokers pick up equal share of old partitions from the kafka brokers running on the old nodes.
- [] Existing pinot segments on the pinot offline servers need to be rebalanced so that they are equally distributed among the old and the new pinot offline server replicas.
	- For metrics tables (kf_metrics and kf_metrics_rollup), this needs to be triggered manually.
	```
	kubectl port-forward -n kfuse pinot-controller-0 9000:9000
	```
	```
	curl -X POST ‘http://localhost:9000/tables/kf_metrics_REALTIME/rebalance?type=REALTIME&dryRun=false&preChecks=false&reassignInstances=true&includeConsuming=true&minimizeDataMovement=DISABLE&bootstrap=false&downtime=true&minAvailableReplicas=0&batchSizePerServer=-1&lowDiskMode=false&bestEfforts=false&externalViewStabilizationTimeoutInMs=3600000&maxAttempts=3&updateTargetTier=false&diskUtilizationThreshold=-1&forceCommit=false&forceCommitBatchSize=2147483647&forceCommitBatchStatusCheckTimeoutMs=180000’
	```
	Optional if Metrics Rollup is enabled
	```
	curl -X POST ‘http://localhost:9000/tables/kf_metrics_rollup_REALTIME/rebalance?type=REALTIME&dryRun=false&preChecks=false&reassignInstances=true&includeConsuming=true&minimizeDataMovement=DISABLE&bootstrap=false&downtime=true&minAvailableReplicas=0&batchSizePerServer=-1&lowDiskMode=false&bestEfforts=false&externalViewStabilizationTimeoutInMs=3600000&maxAttempts=3&updateTargetTier=false&diskUtilizationThreshold=-1&forceCommit=false&forceCommitBatchSize=2147483647&forceCommitBatchStatusCheckTimeoutMs=180000’
	```
	- For all other tables, pinot will automatically trigger a rebalance.

## Validation
1. Monitor the kloudfuse control plane to ensure that kloudfuse stack is running fine - all pods and services should be up and running, pinot segment status should all be GOOD, etc.
2. It might take some time for kafka consumer lags for various topics to be reduced to its normal as the new capacity has to deal with data queued in kafka as well as new incoming data. The consumer lags for various topics should be monitored at the individual topic and partition level to ensure that all partitions are consuming properly.
3. While kafka partition and pinot segment rebalance process is ongoing, expect increase CPU and IO load.
4. Checkin the customer value yaml file in the appropriate customer git repo.
5. Verify that the control plane alerts are no longer firing
6. Control plane overview status is all GREEN
7. Individual stream specific control plane dashboards are all GREEN
8. Kloudfuse UI does not show any lag and recent data is visible
9. Verify that alert rules configured by the customer on the kloudfuse cluster are in “Healthy” state.

---

## Troubleshooting: Pinot Segments Unavailable After Scale Out

### Symptom

After a scale out, `percentSegmentsAvailable` for `kf_metrics` or `kf_metrics_rollup` is persistently low (e.g. 30–40%) and does not recover on its own. The `segmentsInUpdatingState` metric shows thousands of segments stuck — far more than the normal transient count during a healthy rebalance.

### Root Cause

During scale out, disk I/O on Pinot server nodes spikes sharply due to simultaneous segment downloads (rebalancing old segments to new nodes) and segment uploads (committing newly consumed REALTIME segments to deep store). If IOPS are insufficient, S3/GCS upload requests time out.

**Critically: when a deep store upload fails, the server drops to a HOLDING state and retries indefinitely (every ~3 minutes). While it will keep trying, it does not back off or escalate — if S3 remains unavailable or the server is stuck in the retry loop, the segment never becomes ONLINE.** The segment remains stuck in an UPDATING state indefinitely — it will not recover without manual intervention, even after I/O pressure subsides.

### Diagnosis

**Step 1: Confirm the symptom in Kloudfuse Metrics**

Check that `segmentsInUpdatingState` is high and `percentSegmentsAvailable` is persistently low:

```promql
pinot_controller_segmentsInUpdatingState_Value{
  kfuse=”true”,
  table=~”kf_metrics|kf_metrics_rollup”
}

pinot_controller_percentSegmentsAvailable_Value{
  kfuse=”true”,
  table=~”kf_metrics|kf_metrics_rollup”
}
```

A healthy rebalance will show `segmentsInUpdatingState` decreasing steadily. If it stays flat for more than 30 minutes, the uploads have stalled.

**Step 2: Confirm S3 upload failures in Kloudfuse Logs**

Navigate to Kloudfuse UI → **Logs** → **Advanced Search**, set the time range to cover the scale out, and run:

```
source=”pinot-server” and “Failed to upload”
```

You will see repeated errors like:

```
ERROR [S3PinotFS] Failed to upload file /var/pinot/server/data/index/kf_metrics_REALTIME/kf_metrics__N__N__....tar.lz4-java.block to s3://...
```

If these errors appear frequently and then stop (while `segmentsInUpdatingState` stays high), Pinot has exhausted its retries for those segments.

**Step 3: Confirm disk I/O saturation**

In Kloudfuse Metrics, check disk write throughput on pinot-server nodes during the scale out window:

```promql
container_io_write{
  kfuse=”true”,
  app=”pinot”,
  kube_container_name=”server”
}
```

Sustained write throughput at or near the EBS volume limit (e.g. 125 MB/s for a gp2 volume) confirms I/O saturation was the cause.

### Recovery

Segments that have exhausted their upload retries cannot be restarted by a segment reload. The segments need to be reset so Pinot will re-attempt to commit them from the data still available in Kafka (as long as Kafka retention covers the affected time range).

**Step 1: Identify affected segments**

```bash
kubectl port-forward -n kfuse pinot-controller-0 9000:9000 &

# List segments in non-ONLINE state for kf_metrics
curl -s 'http://localhost:9000/tables/kf_metrics_REALTIME/segments' \
  | python3 -c “
import sys, json
data = json.load(sys.stdin)
for entry in data:
    for seg, state in entry.get('segmentStatus', {}).items():
        if state != 'ONLINE':
            print(state, seg)
“
```

**Step 2: Check Kafka retention covers the affected time range**

Identify the earliest timestamp in the affected segment names (format: `kf_metrics__N__N__<TIMESTAMP>`). Confirm Kafka still has data from that time:

```bash
kubectl exec -n kfuse kafka-0 -- \
  kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --describe --group kf_metrics_REALTIME
```

If Kafka retention does not cover the time range, the data for that period is unrecoverable and the segments will need to be deleted (contact Kloudfuse support).

**Step 3: Reset stuck REALTIME segments**

For each segment stuck in a non-ONLINE state, reset it using the Pinot controller API. This causes Pinot to re-consume from Kafka for that segment's partition/offset range:

```bash
# Reset a single segment (replace TABLE and SEGMENT_NAME)
curl -X POST \
  'http://localhost:9000/segments/kf_metrics_REALTIME/<SEGMENT_NAME>/reset'
```

If there are many affected segments, use the [segments-error.sh](alerts/../../scripts/alerts/segments-error.sh) script:

```bash
./segments-error.sh status kf_metrics_REALTIME
./segments-error.sh reset kf_metrics_REALTIME <SEGMENT_NAME>
```

**Step 4: Monitor recovery**

Watch `segmentsInUpdatingState` drop as segments recommit successfully:

```promql
pinot_controller_segmentsInUpdatingState_Value{
  kfuse=”true”,
  table=~”kf_metrics|kf_metrics_rollup”
}
```

And confirm logs show successful uploads:

```
source=”pinot-server” and “kf_metrics” and (“Committed” or “upload” or “ONLINE”)
```

Recovery is complete when `percentSegmentsAvailable` returns to 100% and `segmentsInUpdatingState` is near zero.

### Prevention

- Always increase Pinot server EBS IOPS **before** starting a scale out (see [IOPS Considerations](#iops-considerations-during-scale-out) above).
- During the rebalance, monitor `container_io_write` and `container_io_read` on pinot-server nodes. If write throughput is consistently at the volume ceiling, pause the rebalance and increase IOPS before continuing.
- See also: [Pinot Segments Unavailable](alerts/pinot-segments-unavailable.md)

---

## Troubleshooting: Pinot REALTIME Segments Stuck Due to S3 Upload Timeout

### Symptom

Pinot server logs show repeated errors like:

```
ERROR [S3PinotFS] [pool-N-thread-N] Failed to upload file /var/pinot/server/data/index/kf_logs_REALTIME/kf_logs__0__24285__20260616T0205Z.tar.lz4-java.block to s3://kfuse-storage-eu-prod/kfuse/controller/data/kf_logs/kf_logs__0__24285__20260616T0205Z.tmp.<uuid>
```

The affected REALTIME segments do not appear in query results (data gap) and remain in a non-ONLINE state in the Pinot controller. The cluster does not self-heal.

### Root Cause

When a Pinot server finishes consuming a Kafka segment, it must upload the sealed segment to S3 (deep store) before the controller marks it ONLINE. The upload goes through `PinotFSSegmentUploader`, which runs the S3 copy on a background thread with a configurable timeout (default: 10 seconds server-side).

If the upload times out or fails (S3 connectivity issue, I/O saturation, transient S3 error), the following happens:

1. `PinotFSSegmentUploader` cancels the upload and returns `null`
2. `SplitSegmentCommitter` receives `null` and returns `RESP_FAILED` to the segment data manager
3. The server drops to `HOLDING` state and waits ~3 minutes before retrying the commit protocol
4. On retry, the server attempts the S3 upload again — if S3 is still unavailable, this loop repeats indefinitely

The segment remains stuck in `COMMITTING` state in ZooKeeper. The controller's `uploadToDeepStoreIfMissing` periodic retry job does **not** help here — it only handles segments already in `COMMITTED` state with a missing deep store copy. A segment stuck mid-commit never reaches that state.

### Recovery

The fastest recovery is to **restart the affected Pinot server pods**. On restart:
- The server re-reads the segment from local disk
- It rejoins the commit protocol fresh
- If S3 is healthy, the upload succeeds and the segment becomes ONLINE

```bash
# Identify which pinot-server pods are logging S3 upload failures
kubectl logs -n kfuse -l app=pinot,component=server --tail=200 | grep "Failed to upload"

# Restart the affected server pods (rolling restart of all servers if unsure which)
kubectl rollout restart statefulset/pinot-server -n kfuse

# Monitor recovery — watch for segments becoming ONLINE
kubectl logs -n kfuse -l app=pinot,component=server -f | grep -E "upload|ONLINE|COMMITTED"
```

After restart, confirm the segments recovered by checking `percentSegmentsAvailable` in the Kloudfuse control plane or via:

```promql
pinot_controller_percentSegmentsAvailable_Value{kfuse="true"}
```

> **Note**: The local segment data survives a pod restart as it is on a persistent volume. No data is lost by restarting the server pod, provided the pod comes back up and can reconnect to S3.

### When Pod Restart Is Not Enough

If segments remain stuck after restart, the server may have lost the local segment data (e.g. PVC issue). In that case, check whether Kafka still retains data for the affected time range (see [Step 2 in the previous section](#step-2-check-kafka-retention-covers-the-affected-time-range)) and use the segment reset API to re-consume from Kafka.
