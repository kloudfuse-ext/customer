# Pinot Support Runbook

## Summary

Apache Pinot is a real-time distributed OLAP (Online Analytical Processing) datastore designed for ultra-low-latency analytics on large-scale data. It is used by Kloudfuse to store and serve its metrics, logs, events and traces.  It allows for it to serve real-time data with high throughput and low latency, such as dashboards, anomaly detection, and user-facing analytics.

When Pinot has errors, it is usually due to the server being overloaded with work, the system not having enough memory or disk, or it is not configured with enough internal memory.

## Alert: Pinot Service has Panicked

This alert is looking for a log entry with "_panicLevel"  The Fingerprint for this is,

```
ERROR [PerQueryCPUMemAccountantFactory$PerQueryCPUMemResourceUsageAccountant] [CPUMemThreadAccountant] Heap used bytes (CURRENT_CONFIG), greater than _panicLevel (AMOUNT_USED), Killed all queries and triggered gc!
```

If this alert is being triggered with regularity, it means the system is under stress and needs to be updated to handle a larger workload.

To Resolve this you will need to look at the labels for the Alert, looking for

* kube_cluster_name - The cluster you will need to work with
* kube_service - The name of the kube service that is struggling

The next step is update the values.yaml, to allocate the affected service more memory.

| Kube Service | Update YAML Value |
|--------------|-------------------|
| pinot-broker | pinot.broker.jvmOpts |
| pinot-controller | pinot.controller.jvmOpts |
| pinot-server-realtime | pinot.server.realtime.jvmOpts |
| pinot-server-offline | pinot.server.offline.jvmOpts |

Look for the string *-Xms##G -XmX##G* in jvmOpts. You will need to update the values for both fields by 4.

Example: 

```
Replace: -Xms8G -XmX8G
With: -Xms12G -XmX12G
```

After you have updated the values.yaml you will need to do a helm upgrade to apply these changes.


NOTE: At least half of a nodes memory should be unallocated. There are processes that need to use this memory and it can negatively impact the system if there is not enough available.  If you have questions or problems about make this change contact your Customer Success representative.



