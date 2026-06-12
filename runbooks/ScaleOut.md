# Scale Out Kloudfuse

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
        * Kafka runs in KRaft mode (there is no Kafka ZooKeeper). It is deployed as two StatefulSets:
            * `kafka-kraft-controller` - keep at 3 replicas. These hold the KRaft metadata quorum (odd replica count) and must not be scaled out with the cluster.
            * `kafka-kraft-broker` - scale these out with the cluster to add ingest and storage capacity.
        * for `pinot-zookeeper` keep the number of replicas to 3. This is the only remaining ZooKeeper (used by Pinot) and must not be scaled.
        * for some services such as, kfuse-redis, kfuse-configdb, kfuse-grafana, etc. keep the number of replicas at 1 as these services do not need to be scaled.
        * for all other services increase the number of replicas by appropriate ratio. So, if there were n nodes and m new nodes are being added, the replicas should be scaled up `(n + m) / n` factor.
    * Increase the number of partitions based on the increased volume as well as expected increase in the volume. Each of the streams such as, logs, metrics, APM have their specific topics for ingest, tranformers as well as for pinot. They all need to be increased in the right proportion.
        * When increasing partitions, size the kafka-kraft broker disk accordingly using `diskSpace = numberOfPartitions * replicationFactor * 10GB` (the default per-partition retention is 10GB, set by `kafka.logRetentionBytes`). Set `kafka-kraft.broker.persistence.size` in the customer values yaml to match.
    * Get the customer value yaml file reviewed by the CS as well as engineering team.
    
### Execution      
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
	curl -X POST 'http://localhost:9000/tables/kf_metrics_REALTIME/rebalance?type=REALTIME&dryRun=false&preChecks=false&reassignInstances=true&includeConsuming=true&minimizeDataMovement=DISABLE&bootstrap=false&downtime=true&minAvailableReplicas=0&batchSizePerServer=-1&lowDiskMode=false&bestEfforts=false&externalViewStabilizationTimeoutInMs=3600000&maxAttempts=3&updateTargetTier=false&diskUtilizationThreshold=-1&forceCommit=false&forceCommitBatchSize=2147483647&forceCommitBatchStatusCheckTimeoutMs=180000'
	```
	Optional if Metrics Rollup is enabled
	```
	curl -X POST 'http://localhost:9000/tables/kf_metrics_rollup_REALTIME/rebalance?type=REALTIME&dryRun=false&preChecks=false&reassignInstances=true&includeConsuming=true&minimizeDataMovement=DISABLE&bootstrap=false&downtime=true&minAvailableReplicas=0&batchSizePerServer=-1&lowDiskMode=false&bestEfforts=false&externalViewStabilizationTimeoutInMs=3600000&maxAttempts=3&updateTargetTier=false&diskUtilizationThreshold=-1&forceCommit=false&forceCommitBatchSize=2147483647&forceCommitBatchStatusCheckTimeoutMs=180000'
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

## Troubleshooting

### Newly added broker fails with `INCONSISTENT_CLUSTER_ID` (errorCode 104)

**Symptom:** After scaling out from `N` to `N+1` (or more) brokers, the newly added `kafka-kraft-broker-<N>` pod(s) never become ready, and their logs show repeated errors fetching from every controller. In the example below, the new broker is `kafka-kraft-broker-3` (raft `id=103`), but this applies to whichever broker ordinal(s) were just added:

```
kubectl logs -n kfuse kafka-kraft-broker-<N>
...
ERROR [RaftManager id=10<N>] Unexpected error INCONSISTENT_CLUSTER_ID in FETCH response: InboundResponse(correlationId=..., data=FetchResponseData(..., errorCode=104, ...), source=kafka-kraft-controller-0.kafka-kraft-controller-headless.kfuse.svc.cluster.local:9093 ...) (org.apache.kafka.raft.KafkaRaftClient)
```

**Cause:** Each broker reads the KRaft cluster id **once** from the `kafka-kraft-kraft-cluster-id` secret on first startup, then persists it to its own `/bitnami/kafka/data/meta.properties` and never reads the secret again. A newly added broker reads whatever value the secret currently holds. If the secret is missing or no longer matches the rest of the cluster, the new broker writes a cluster id that does not match the controllers, and KRaft rejects all of its FETCH requests with `INCONSISTENT_CLUSTER_ID` (errorCode 104).

Helm only **creates** the `kafka-kraft-kraft-cluster-id` secret if it does not already exist (it never overwrites it). So if someone deleted the secret, the next helm upgrade regenerated it with a **new, random** cluster id — which then mismatches the existing controllers and brokers that still carry the original id. This is the usual root cause.

> ⚠️ The cluster id you pin **must** equal the id the existing controllers already use. Pinning a different value, or letting helm regenerate a random one, will break the entire Kafka cluster, not just the new broker(s).

**Resolution:**

1. Read the actual cluster id from a healthy controller (this is the source of truth — the controllers hold the real id in their persisted `meta.properties`):

   ```bash
   kubectl exec -n kfuse kafka-kraft-controller-0 -- grep cluster.id /bitnami/kafka/data/meta.properties
   ```

   Optionally cross-check it against the current secret value:

   ```bash
   kubectl get secret -n kfuse kafka-kraft-kraft-cluster-id -o jsonpath='{.data.*}' | base64 -d
   ```

2. Pin that exact cluster id in the customer values yaml under the `kafka-kraft` section:

   ```yaml
   kafka-kraft:
     kraft:
       clusterId: "<value from step 1>"
   ```

3. Run `helm upgrade` using the **same version as currently installed** (pinning `clusterId` makes helm reconcile the secret to the correct value):

   ```bash
   helm upgrade <release> <chart> -n kfuse -f <customer-values.yaml> --version <installed-version>
   ```

4. For **each** newly added broker that logged `INCONSISTENT_CLUSTER_ID`, delete its PVC and pod so it re-initializes its `meta.properties` from the now-correct secret (the StatefulSet recreates the pod automatically). Replace `<N>` with the affected broker ordinal:

   ```bash
   N=<broker-ordinal>   # e.g. 3, or repeat for each newly added broker
   kubectl delete pvc -n kfuse "data-kafka-kraft-broker-${N}"
   kubectl delete pod -n kfuse "kafka-kraft-broker-${N}"
   ```

5. Confirm each recreated pod reaches `Running` and the `INCONSISTENT_CLUSTER_ID` errors stop:

   ```bash
   kubectl get pods -n kfuse | grep kafka-kraft-broker
   kubectl logs -n kfuse "kafka-kraft-broker-${N}" --tail=50
   ```

**Alternative (secret was deleted):** If you confirm the secret is missing or wrong, you can instead let helm recreate it from the pinned value — delete the secret **after** pinning `kraft.clusterId` in step 2 (never delete it without pinning, or helm will generate a fresh random id), then helm upgrade and delete the affected broker(s)' pvc/pod as in steps 4–5:

```bash
kubectl delete secret -n kfuse kafka-kraft-kraft-cluster-id
helm upgrade <release> <chart> -n kfuse -f <customer-values.yaml> --version <installed-version>
N=<broker-ordinal>
kubectl delete pvc -n kfuse "data-kafka-kraft-broker-${N}"
kubectl delete pod -n kfuse "kafka-kraft-broker-${N}"
```
