Kloudfuse Retention Policy and Kafka Partition Configuration
============================================================

Kloudfuse supports both **default** and **custom** retention policies for various data streams.  
If you want to add a custom retention policy to specific streams, you must update the **Kafka partition configuration** to account for the additional retention class.

### Updating Partition Count with Custom Retention Classes

When a custom retention class is added, you'll have both the default and custom class(es).  
To calculate the updated number of partitions:

1. Determine the current **partitions per topic per node**.
2. Use this formula: *New number of partitions = (Current Total number of partitions / Current number of classes) * new total number of clases *
> **Note:**  
> Number of retention classes = `1 (default)` + `number of custom classes`

### Make the change in following kafka topics

This change applies to the following topics:

- `kf_metrics_topic`
- `kf_logs_topic`
- `kf_traces_topic`
- `kf_traces_errors_topic`
- `kf_events_topic`

### Size the Kafka broker disk for the added partitions

Adding partitions for a custom retention class increases the total disk required on the kafka-kraft brokers. Size the broker disk using:

> `diskSpace = numberOfPartitions * replicationFactor * 10GB`

where 10GB is the default per-partition retention (`kafka.logRetentionBytes`). Update `kafka-kraft.broker.persistence.size` in the customer values yaml to match the new partition count before applying the change.

### Rebalance after increasing partitions

After the partition count is increased, run a [kafka rebalance](kafka-rebalance.md) so the new partitions are evenly distributed across all brokers.