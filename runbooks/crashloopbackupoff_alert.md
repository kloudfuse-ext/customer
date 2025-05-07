# Alert: Pod experiencing CrashLoopBackOff Error

## Summary

When a Kubernetes container repeatedly fails to start, it enters a ‘CrashLoopBackOff’ state, indicating a persistent restart loop for that pod. This error often occurs due to various issues preventing the container from launching properly.

By default, a pod’s restart policy is *Always*. Depending on the restart policy defined in the pod template, Kubernetes might try to restart the pod multiple times. When a Pod state is displaying CrashLoopBackOff, it is waiting a certain amount of time before restarting the pod again. 

## Common Causes

### Resource Constraints

One of the common causes of the CrashLoopBackOff error is resource overload or insufficient memory. Kubernetes allows setting memory and CPU usage limits for each pod, which means your application might be crashing due to insufficient resources.

### Application Errors

The application is unable start and instead exits and the Pod is not able to start

### Configuration Errors

Possible configuration errors are,

* Runtime dependencies are missing (*for example:* var, run, secrets or service account files are missing)
* configuration files (via ConfigMaps)
* incorrect environment variables

These could keep the application from running and therefor the Pod from starting.

### Probes are Misconfigured

The Readiness probe or Liveness Probe failing if the application does not respond within the specified timeframe.  If the time period is too small it might be prematurely failing.

## Troubleshooting

### General Approaches for Troubleshootin

* Inspect events: Use kubectl describe pod <name-of-pod> to see Pod events.  This is a good first place to check to see why Kubernetes cannot start the Pod.  If it is a specific Kubernetes issue it should show up here.
* Check resource limits: Kubernetes assigns containers CPU and memory. If the application needs more resources than what Kubernetes allocated it can prevent it from starting. Increase the resources in the Pod definition can resolve the issue.
* Check logs: Use kubectl logs <name-of-pod> to check the container logs. If there are application or service errors, this is the most likely place you will the messages for it.
* Review configuration: Applications will often depend upon environment variables and mounted volumes for configuring the application.  If Secrets or volumes cannot be mounted, the application might not be able to start.
* File Permission Issues: Another possible configuration problem can be the application is attempting to write files to a Read-Only file system.
* Debug application: There might be bug in the application itself preventing it from starting. You can run this container locally or in a development environment to help diagnose these types of issues.

## Kfuse Specific Errors

### Any Pod: Unable to retrieve some image pull secrets (kfuse-image-pull-credentials)

Do a `kubectl describe po <pod_name> and check the events section

```
Events:
  Type     Reason                           Age                     From               Message
  ----     ------                           ----                    ----               -------
  Normal   Scheduled                        4m27s                   default-scheduler  Successfully assigned kfuse/pinot-events-table-creation-std6v to gke-dev-gcp-spot-pool-2-28700bac-pkg5
  Warning  FailedMount                      4m26s                   kubelet            MountVolume.SetUp failed for volume "kube-api-access-bd8r9" : failed to fetch token: serviceaccounts "default" is forbidden: node requested token bound to a pod scheduled on a different node
  Warning  FailedMount                      4m26s                   kubelet            MountVolume.SetUp failed for volume "kfuse-pinot-events-schema" : failed to sync configmap cache: timed out waiting for the condition
  Normal   Created                          3m39s (x3 over 4m24s)   kubelet            Created container: pinot-add-table-json
  Normal   Started                          3m38s (x3 over 4m24s)   kubelet            Started container pinot-add-table-json
  Warning  BackOff                          3m14s (x3 over 3m54s)   kubelet            Back-off restarting failed container pinot-add-table-json in pod pinot-events-table-creation-std6v_kfuse-steve-runbook(6e6cdee9-3288-443d-8df4-eecf0559ac04)
  Warning  FailedToRetrieveImagePullSecret  2m59s (x10 over 4m25s)  kubelet            Unable to retrieve some image pull secrets (kfuse-image-pull-credentials); attempting to pull the image may not succeed.
  Normal   Pulled                           2m59s (x4 over 4m24s)   kubelet            Container image "us.gcr.io/mvp-demo-301906/pinot:1.3.0-c2f04c5edf" already present on machine
```

If you see the `Unable to retrieve some image pull secrets (kfuse-image-pull-credentials)` It means that secret is missing from the namespace. You will need to add the secret object
running this command.

```
kubectl create secret docker-registry kfuse-image-pull-credentials \
        --namespace='kfuse' --docker-server 'us.gcr.io' --docker-username _json_key \
        --docker-email 'container-registry@mvp-demo-301906.iam.gserviceaccount.com' \
        --docker-password=''"$(cat token.json)"''
```

The token.json is the credentials giving to you to access the above registry.

### Pod: kfuse-kafka-topic-creation

do a `kubectl logs <pod_name>`  Check for this error message.

```
+ /opt/bitnami/kafka/bin/kafka-topics.sh --alter --bootstrap-server kafka:9092 --partitions 2 --topic logs_ingest_topic
[2025-05-07 21:38:03,619] WARN [AdminClient clientId=adminclient-1] The DescribeTopicPartitions API is not supported, using Metadata API to describe topics. (org.apache.kafka.clients.admin.KafkaAdminClient)
Error while executing topic command : Topic currently has 3 partitions, which is higher than the requested 2.
[2025-05-07 21:38:03,671] ERROR org.apache.kafka.common.errors.InvalidPartitionsException: Topic currently has 3 partitions, which is higher than the requested 2.
 (org.apache.kafka.tools.TopicCommand)
```

It means that in the values.yaml you change the number of partions down from what is currently configured.  You cannot go down, only up.  Look for this section for the number of partions

```
    - name: logs_ingest_topic
      partitions: 2 # Changed from 3, will cause the above error
      replicationFactor: 1
```
You will need to update the partion to the same or a higher number than it was previously.  You will also need to delete this job before you can do another helm upgrade.

`helm delete job kfuse-kafka-topic-creation`

### Pod: kfuse-set-tag-hook-pinot

do a `kubectl logs <pod_name>`  Check for this error message.

```
Setting tag for realtime server '0'
  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
  0     0    0     0    0     0      0      0 --:--:-- --:--:-- --:--:--     0
curl: (7) Failed to connect to pinot-controller port 9000 after 8 ms: Couldn't connect to server
```

It means that the realtime server has not completed its configuration yet.  After other jobs have run getting the Pinot realtime server up it should complete.

### Pod:
        
