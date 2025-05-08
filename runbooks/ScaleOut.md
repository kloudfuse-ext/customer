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
        * for zookeeper (kafka zookeeper and pinot zookeeper) keep the number of replicas to 3.
        * for some services such as, kfuse-redis, kfuse-configdb, kfuse-grafana, etc. keep the number of replicas at 1 as these services do not need to be scaled.
        * for all other services increase the number of replicas by appropriate ratio. So, if there were n nodes and m new nodes are being added, the replicas should be scaled up `(n + m) / n` factor.
    * Increase the number of partitions based on the increased volume as well as expected increase in the volume. Each of the streams such as, logs, metrics, APM have their specific topics for ingest, tranformers as well as for pinot. They all need to be increased in the right proportion.
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
	curl -X POST 'http://localhost:9000/tables/kf_metrics_REALTIME/rebalance?type=REALTIME&dryRun=false&reassignInstances=true&includeConsuming=false&bootstrap=false&downtime=true&bestEfforts=false&lowDiskMode=false&minAvailableReplicas=1'
	```
	Optional if Metrics Rollup is enabled
	```
	curl -X POST 'http://localhost:9000/tables/kf_metrics_rollup_REALTIME/rebalance?type=REALTIME&dryRun=false&reassignInstances=true&includeConsuming=false&bootstrap=false&downtime=true&bestEfforts=false&lowDiskMode=false&minAvailableReplicas=1'
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
