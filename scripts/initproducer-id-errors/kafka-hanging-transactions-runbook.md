# Kafka Hanging Transactions Runbook

## Overview
This runbook provides step-by-step instructions for identifying and resolving hanging Kafka transactions in a Kubernetes cluster.

## Prerequisites
- kubectl access to the cluster with appropriate permissions
- Kubernetes context set to the target cluster (e.g., iris cluster)
- Access to Kafka broker pods in the cluster

## Step-by-Step Instructions

### 1. Identify Kafka Broker Pods
First, list all Kafka broker pods in the cluster:

```bash
kubectl get pods -A | grep -i kafka
```

Expected output:
```
kfuse          kafka-broker-0                                             1/1     Running   0                8d
kfuse          kafka-broker-1                                             1/1     Running   0                7d8h
kfuse          kafka-broker-2                                             1/1     Running   0                3h28m
```

### 2. Find Hanging Transactions
Check each broker for hanging transactions. Execute the following commands for each broker ID (0, 1, 2):

```bash
# For broker 0
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 find-hanging --broker-id 0"

# For broker 1
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 find-hanging --broker-id 1"

# For broker 2
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 find-hanging --broker-id 2"
```

**Note:** The `unset JMX_PORT` is crucial to avoid port conflicts.

Sample output showing hanging transactions:
```
Topic        	Partition	ProducerId	ProducerEpoch	CoordinatorEpoch	StartOffset	LastTimestamp	Duration(min)	
kf_logs_topic	3        	4000      	15937        	514             	1193596434 	1747728095380	32825
```

**Important fields to note:**
- **Topic**: The topic name where the hanging transaction exists
- **Partition**: The partition number within that topic
- **StartOffset**: The offset where the transaction began (REQUIRED for abort command)
- **Duration(min)**: How long the transaction has been hanging (in minutes)

### 3. Abort Hanging Transactions
For each hanging transaction identified, use the StartOffset value from the find-hanging output:

```bash
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 abort --topic <TOPIC_NAME> --partition <PARTITION_NUMBER> --start-offset <START_OFFSET>"
```

Example using the sample output above:
```bash
# Using values from the find-hanging output:
# Topic: kf_logs_topic, Partition: 3, StartOffset: 1193596434
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 abort --topic kf_logs_topic --partition 3 --start-offset 1193596434"
```

### 4. Verify Transaction Cleanup
After aborting the transactions, verify they have been cleared by re-running the find-hanging command for each broker:

```bash
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 find-hanging --broker-id 0"
```

The output should show no hanging transactions:
```
Topic	Partition	ProducerId	ProducerEpoch	CoordinatorEpoch	StartOffset	LastTimestamp	Duration(min)
```

## Troubleshooting

### JMX Port Error
If you encounter this error:
```
Error: JMX connector server communication error: service:jmx:rmi://kafka-broker-0:5555
java.net.BindException: Address already in use
```

**Solution:** Always include `unset JMX_PORT` before running kafka-transactions.sh commands.

### Script Not Found
If kafka-transactions.sh is not found, verify its location:
```bash
kubectl exec -n kfuse kafka-broker-0 -- find / -name "kafka-transactions.sh" 2>/dev/null
```

The script is typically located at: `/opt/bitnami/kafka/bin/kafka-transactions.sh`

### Permission Denied
Ensure you have the necessary kubectl permissions to exec into pods in the target namespace (usually `kfuse`).

## Important Notes

1. **Always check all brokers** - Hanging transactions can occur on any broker
2. **Document findings** - Record the ProducerId, topic, partition, and duration of hanging transactions
3. **Impact assessment** - Long-running hanging transactions (duration in thousands of minutes) indicate serious issues
4. **Namespace** - The examples use `kfuse` namespace; adjust based on your deployment

## Quick Reference Commands

```bash
# List Kafka pods
kubectl get pods -n kfuse | grep kafka-broker

# Find hanging transactions (replace X with broker ID)
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 find-hanging --broker-id X"

# Abort hanging transaction
kubectl exec -n kfuse kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-transactions.sh --bootstrap-server localhost:9092 abort --topic TOPIC_NAME --partition PARTITION_NUM --start-offset START_OFFSET"
```

## When to Escalate

Escalate to the engineering team if:
- Hanging transactions reappear frequently after cleanup
- The same ProducerId repeatedly creates hanging transactions
- Transaction duration exceeds 10,000 minutes
- Aborting transactions fails or causes errors
- Performance degradation continues after cleanup

## Additional Resources

- [Apache Kafka Documentation](https://kafka.apache.org/documentation/)
- Internal Kafka monitoring dashboards
- Kafka broker logs: `kubectl logs -n kfuse kafka-broker-X`