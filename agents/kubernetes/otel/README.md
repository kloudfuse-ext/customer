# Kubernetes — OpenTelemetry Collector

Values for the upstream
[`open-telemetry/opentelemetry-collector`](https://github.com/open-telemetry/opentelemetry-helm-charts/tree/main/charts/opentelemetry-collector)
Helm chart that send a Kubernetes cluster's telemetry to Kloudfuse over OTLP HTTP.
One install per cluster. Full guide: [OTel Collector on Kubernetes](https://docs.kloudfuse.com/platform/latest/integration/otel/kubernetes/).

## What it collects

The Collector runs as a DaemonSet, one pod per node.

| Scope | Data | Runs on |
|---|---|---|
| Node | Container logs, kubelet node/pod/container/volume metrics, host metrics, OTLP traces/metrics/logs from your apps | Every pod |
| Cluster | `k8s_cluster` metrics, Kubernetes events, Kubernetes objects | One pod at a time, chosen by leader election |

Kubernetes objects include ConfigMaps, which are sent in full. If some of yours hold secrets, limit or remove the `configmaps` entry as the comment in the file describes.

Optional, commented out in the file: scraping Prometheus metrics from pods annotated `prometheus.io/scrape: "true"`.

Records carry:

- **Cluster name** (`k8s.cluster.name`, shown in Kloudfuse as `kube_cluster_name`), when it is detected or set.
- **Cloud account** (`cloud.account.id`, shown as `cloud_account_id`): the AWS account, GCP project or Azure subscription. Not set on-premises.
- **GCP project** (`project`), on GKE only. Other clouds have no projects, so `project` is not set there.

Cluster-level data has the node's host attributes removed, so deployments, events and objects are not reported as coming from the node that holds the lease.

## Prerequisites

- Helm 4.0 or later, which the chart requires. Chart 0.178.3 also renders with Helm 3.17, but only Helm 4 was used to install it in testing.
- Chart 0.162.0 or later; Collector Contrib 0.153.0 or later.
- The external hostname of your Kloudfuse cluster.
- An API key, if ingestion authentication is enabled.
- Nodes that run DaemonSets. EKS clusters that run only on Fargate are not supported.
- **EKS only:** `ec2:DescribeInstances` on the node or Collector IAM role, and pod access to instance metadata (IMDSv2 hop limit 2 or more). Otherwise set the cluster name yourself.

## Deploy

1. Edit `helm-values.yaml`: set `KLOUDFUSE_ENDPOINT`, and uncomment `OTEL_RESOURCE_ATTRIBUTES` to set the cluster name wherever it is not detected correctly: anywhere other than GKE, EKS and AKS; on EKS without the permissions listed above; and on AKS when the cluster name contains an underscore or the node resource group has a custom name.
2. Store the API key (skip if ingestion authentication is off):

   ```bash
   kubectl create namespace otel --dry-run=client -o yaml | kubectl apply -f -
   kubectl -n otel create secret generic kloudfuse-api-key \
     --from-literal=api-key='<your Kloudfuse API key>' \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

   These commands can be run again to change the key. Then restart the Collector pods:

   ```bash
   kubectl -n otel rollout restart daemonset -l app.kubernetes.io/instance=kloudfuse-otel
   ```

3. Install:

   ```bash
   helm repo add open-telemetry https://open-telemetry.github.io/opentelemetry-helm-charts
   helm repo update
   helm upgrade --install kloudfuse-otel open-telemetry/opentelemetry-collector \
     --version 0.178.3 -n otel --create-namespace -f helm-values.yaml
   ```

## Verify

- `kubectl -n otel get pods -l app.kubernetes.io/instance=kloudfuse-otel -o wide` shows one pod on every node you expect. A node with a `NoSchedule` or `NoExecute` taint gets no pod, and so sends no logs or metrics, until you uncomment the `tolerations` block in `helm-values.yaml` and install again.
- In Kloudfuse, filter metrics by `kube_cluster_name="<cluster-name>"` and `kf_metrics_agent="otlp"`.
- *Infrastructure > Kubernetes* lists the cluster's objects; filter by `kf_infra_agent=otlp`.
- Kubernetes events are in *Events* with `kf_events_agent="otlp"`.
- If the pods run but no data arrives and your Kloudfuse requires an API key, check that the Secret `kloudfuse-api-key` exists in the `otel` namespace. The Collector starts without it, so a missing or wrong key shows only as rejected requests in the Collector's log.

## Tear down

```bash
helm uninstall kloudfuse-otel -n otel
```
