import re
import subprocess

GET_BROKER_IDS=   "kubectl exec kafka-zookeeper-0 -- /opt/bitnami/zookeeper/bin/zkCli.sh -server localhost:2181 ls /brokers/ids"
GET_KAFKA_TOPICS= 'kubectl exec kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server :9092 --list"'
GET_REASSIGN_PLAN='kubectl exec kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-reassign-partitions.sh --bootstrap-server :9092 --generate --topics-to-move-json-file /tmp/topics.json --broker-list {}"'
EXECUTE_PLAN=     'kubectl exec kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-reassign-partitions.sh --bootstrap-server :9092 --execute --reassignment-json-file /tmp/updated_config.json"'
MONITOR_PLAN=     'kubectl exec kafka-broker-0 -- bash -c "unset JMX_PORT && /opt/bitnami/kafka/bin/kafka-reassign-partitions.sh --bootstrap-server :9092 --verify  --reassignment-json-file /tmp/updated_config.json"'
UPLOAD_FILE_TO_POD='kubectl cp {file_name} kafka-broker-0:/tmp/{file_name}'

PINOT_REBALANCE = 'kubectl exec pinot-controller-0 -- bash -c "curl -X POST \'http://localhost:9000/tables/{}/rebalance?type=REALTIME&dryRun=false&reassignInstances=true&includeConsuming=false&bootstrap=false&downtime=true&bestEfforts=false&lowDiskMode=false&minAvailableReplicas=1\'"'
PINOT_TABLES    = ['kf_metrics_REALTIME','kf_metrics_rollup_REALTIME']

broker_ids = None
cluster_kafka_topics = None
broker_reassign_plan = None
plan_partitions = {}

def execute_plan():
    print("Executing plan...")
    result = subprocess.run(EXECUTE_PLAN, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed to get reassignment plan for kafka-broker: {} {}".format(result.stdout, result.stderr))
        exit(1)

    for line in result.stdout.splitlines():
        match = re.search("Successfully started partition reassignments for (.+)", line)
        if match:
            global plan_partitions
            for parition in match.group(1).split(','):
                plan_partitions[ parition ] = "in progress"
            return

    print("..Failed to start partition reassignment\n{}".format(result.stdout))
    return

def get_broker_ids():
    print("Fetching Broker ids from kafka-zookeeper")
    result = subprocess.run(GET_BROKER_IDS, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("..Failed to connect {}{}".format(result.stdout,result.stderr))
        exit(1)

    match = re.search("\\[([\\d, ]+)\\]", result.stdout, re.MULTILINE)
    if not match:
        print("..Could not find broker ids from response '{}'".format(result.stdout))
        exit(1)

    ids = match.group(1).split(', ')
    if len(ids) == 0:
        print("..Could parse out broker ids from response '{}'".format(result.stdout))
        exit(1)
    print("..Found {} brokers. Their Ids are {}".format(len(ids), ids))
    global broker_ids
    broker_ids = ids
    return

def get_kafka_reassign_plan():
    print("Fetching reassignment plan for kafka-broker")
    assign_plan = GET_REASSIGN_PLAN.format(','.join( broker_ids ))
    result = subprocess.run(assign_plan, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("..Failed to connect{}{}".format(result.stdout, result.stderr))
        exit(1)
    global broker_reassign_plan
    broker_reassign_plan = result.stdout.split('\n')
    return

def get_kafka_topics():
    print("Fetching Kafka topics from kafka-broker")
    result = subprocess.run(GET_KAFKA_TOPICS, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("..Failed to connect {}{}".format(result.stdout, result.stderr))
        exit(1)

    kafka_topics = []
    for line in result.stdout.splitlines():
        if re.search("^[a-zA-Z]+", line):
            kafka_topics.append(line)

    if len(kafka_topics) == 0:
        print("Could parse out kafka topics from this output '{}'".format(result.stdout))
        exit(1)
    print("..{} kafka topics found".format(len(kafka_topics)))
    global cluster_kafka_topics
    cluster_kafka_topics = kafka_topics
    return

def monitor_plan():
    print("monitoring plan...")
    print("..NOTE: If the script is closed early you can check the plan status by running\n..{}\n".format(MONITOR_PLAN))

    global plan_partitions
    while True:
        result = subprocess.run(MONITOR_PLAN, shell=True, capture_output=True, text=True)
        if result.returncode != 0:
            print("..ERROR: monitoring the reassignment plan: {} {}".format(result.stdout, result.stderr))
            exit(1)

        for line in result.stdout.splitlines():
            match = re.search("Reassignment of partition (.+?) is completed.", line)
            if not match:
                continue

            plan_partitions[ match.group(1) ] = 'complete'

        no_partions  = len(plan_partitions.keys())
        no_completed = 0
        for status in plan_partitions.values():
            if status == 'complete':
                no_completed += 1

        if no_completed == no_partions:
            break

        print("..Partions Completed: {}".format(int(no_completed / no_partions * 100)))
    print("All partitions have been updated")
    return

def rebalance_pinot():
    print("rebalancing pinot tables...")
    print("..NOTE: This can take a while to finish.  So completion is not confirmed in this script.\n")
    for table in PINOT_TABLES:
        curl_cmd = PINOT_REBALANCE.format(table)
        result = subprocess.run(curl_cmd, shell=True, capture_output=True, text=True )
        if result.returncode != 0:
            print("..Failed to execute rebalancing for {}".format(table))
            print("..Run this command manually\n\n{}\n".format(curl_cmd))
        else:
            print("..Successfully executed rebalancing for {}".format(table))
    return

def save_file( option ):
    file_name = "{}.json".format( option )

    content = _file_topics() if option == 'topics' else _file_plan( option )

    tgt_file = open(file_name, "w")
    tgt_file.write( content )
    tgt_file.close()

    return file_name

def upload_file( file_name ):
    print("Uploading {} file to Pod".format(file_name))
    result = subprocess.run(UPLOAD_FILE_TO_POD.format( file_name=file_name ), shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print("Failed to upload {} to kafaka-broker {}".format(file_name, result.stderr))
        exit(1)
    print("..upload complete".format(file_name))
    return

def _file_plan( option ):
    match = 'Current partition replica assignment'
    if option == 'updated_config':
        match = 'Proposed partition reassignment configuration'

    global broker_reassign_plan
    fetch_line = 0
    for line in broker_reassign_plan:
        fetch_line += 1
        if match == line:
            break
    return broker_reassign_plan[fetch_line]

def _file_topics():
    formatted_topics = []
    global cluster_kafka_topics
    for topic in cluster_kafka_topics:
        formatted_topics.append('        {"topic": "' + topic + '"}')

    topics_content = """
    {{
        "version" : 1,
        "topics" : [
    {}
        ]
    }}
    """
    return topics_content.format(",\n".join(formatted_topics))

if __name__ == '__main__':
    get_broker_ids()
    get_kafka_topics()
    save_file('topics')
    upload_file('topics.json')
    get_kafka_reassign_plan()
    save_file('updated_config')
    save_file('current_config')
    upload_file('updated_config.json')
    execute_plan()
    rebalance_pinot()

    monitor_plan()
    exit(0)
