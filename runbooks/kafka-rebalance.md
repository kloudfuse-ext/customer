# How to Rebalance Kafka Partitions After Adding Brokers

When you scale your Apache Kafka cluster by adding more broker instances, you also need to **rebalance** the partition distribution to make use of the new capacity. Kafka does **not** automatically redistribute partitions, so if you skip rebalancing, your new brokers sit idle while old ones remain overloaded.

This guide walks through how to rebalance Kafka partitions using the CLI tools, including how to get the broker list from ZooKeeper.

---

## 📌 Why Rebalancing Is Needed

- New Kafka brokers do not automatically take on any partition leadership or replicas.
- Existing brokers continue to handle the full load.
- Rebalancing spreads the load and improves performance and fault tolerance.

---

## 🔧 Step-by-Step: Kafka Rebalancing Guide

### ✅ Step 0: Get the Broker List from ZooKeeper

Use it if partitions are imbalanced. You can check the data directory to see if there is imbalance.

Find the # of replicas and their usage

```bash
$ num_replicas=$(kubectl get statefulsets.apps kafka | grep -v "NAME" | awk '{print $2}' | awk -F'/' '{print $2}')

$ for i in 0 1 2 3 4 5 6 7 8;do echo "usage for kafka-broker-${i}"; kubectl exec -it kafka-broker-${i} -- du -hd1 /bitnami/kafka/data | grep -v "__consumer" | grep -v "__transaction" ; done
```


### ✅ Step 1: Get the Broker List from ZooKeeper

If you're using ZooKeeper (not KRaft mode), get the list of broker IDs like this:

```bash
zkCli.sh -server localhost:2181
```

Then run inside the shell:

```bash
ls /brokers/ids
```

You'll get output like:

```
[100, 101, 102, 103]
```

Use these broker IDs in your reassignment plan.

Exit the shell with:

```bash
quit
```

---

### ✅ Step 2: View Current Partition Distribution

You can inspect how partitions are currently distributed across brokers:

```bash
kubectl exec -ti -n kfuse kafka-broker-0 -- bash
unset JMX_PORT
/opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server :9092 --list
```

---

### ✅ Step 3: Create a Topics JSON File

You’ll need a JSON file listing the topics to rebalance. Create a file called `topics.json` with the list of topics from the list command:

```bash
cat > > /bitnami/kafka/topics.json
```

```json
{
  "version": 1,
  "topics": [
    { "topic": "kf_events_topic" },
    { "topic": "kf_logs_metric_topic" },
    { "topic": "kf_logs_topic" },
    { "topic": "kf_metrics_topic" },
    { "topic": "kf_traces_errors_topic" },
    { "topic": "kf_traces_metric_topic" },
    { "topic": "kf_traces_topic" },
    { "topic": "logs_ingest_topic" }
  ]
}
```
---

### ✅ Step 4: Generate a Reassignment Plan

Now generate a plan using the list of broker IDs you got earlier:

```bash
kafka-reassign-partitions.sh \
  --bootstrap-server :9092 \
  --generate \
  --topics-to-move-json-file topics.json \
  --broker-list "100,101,102,103" > reassign-plan.json
```

This writes a JSON plan to `reassign-plan.json`.

---

### ✅ Step 5: Review the Plan

Open and review `reassign-plan.json`. It should look like:

```json
{
  "version": 1,
  "partitions": [
    {
      "topic": "your-topic",
      "partition": 0,
      "replicas": [2, 3],
      "log_dirs": ["any", "any"]
    }
  ]
}
```

The above command will print out the `Current partition replica assignment` and `Proposed partition reassignment configuration`. Ignore the proposed output. Only the `Proposed partition reassignment` is needed. 

Don't save the files in `/tmp` directory as that directory gets cleared up on pod restart. Instead save it in `/bitnami/kafka` directory (which is on pvc) Save the `Current partition replica assignment` to `topics.current.json` file Save the `Proposed partition reassignment` to `topics.balanced.json` file. Format the `Proposed partition replica assignment` in standard JSON format and make sure it looks reasonable and distributes partitions across all brokers.

---

### ✅ Step 6: Execute the Reassignment

Apply the plan:

```bash
kafka-reassign-partitions.sh \
  --bootstrap-server :9092 \
  --execute \
  --reassignment-json-file /bitnami/kafka/topics.balanced.json
```

---

### ✅ Step 7: Monitor the Progress

You can verify the reassignment is in progress or completed:

```bash
kafka-reassign-partitions.sh \
  --bootstrap-server :9092 \
  --verify \
  --reassignment-json-file /bitnami/kafka/topics.balanced.json
```

---

## ⚠️ Best Practices

- Run rebalancing during off-peak hours to avoid performance impact.
- In large clusters, consider moving a subset of partitions at a time.
---

## 🧠 Wrapping Up

Adding Kafka brokers is just step one. Without rebalancing, you won’t get the performance boost or reliability benefits of a bigger cluster. Use the steps above to do it right and ensure your cluster is balanced and efficient.:1

