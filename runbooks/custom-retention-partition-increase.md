Kloudfuse Retention Policy and Kafka Partition Configuration
============================================================

Kloudfuse supports both **default** and **custom** retention policies for various data streams.  
If you want to add a custom retention policy to specific streams, you must update the **Kafka partition configuration** to account for the additional retention class.

### Default Kafka Topics Partitions Example

- Each topic typically has **2** or **4** partitions per node.
- In a 3-node cluster:
  - 2 partitions per node → `2 × 3 = 6` total partitions
  - 4 partitions per node → `4 × 3 = 12` total partitions

### Updating Partition Count with Custom Retention Classes

When a custom retention class is added, you'll have both the default and custom class(es).  
To calculate the updated number of partitions:

1. Determine the current **partitions per topic per node**.
2. Use this formula: *Total partitions = (Partitions per node) × (Number of nodes) × (Number of retention classes)*
> **Note:**  
> Number of retention classes = `1 (default)` + `number of custom classes`

### Make the change in following kafka topics

This change applies to the following topics:

- `kf_metrics_topic`
- `kf_logs_topic`
- `kf_traces_topic`
- `kf_traces_errors_topic`
- `kf_events_topic`