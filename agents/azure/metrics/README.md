# Azure Metrics → Kloudfuse

Validates the Azure metrics integration documented at `data-collection/cloud-services/azure/metrics.adoc`.

The Cloud Exporter runs inside the Kloudfuse cluster and polls the Azure Monitor Metrics API every 5 minutes using a Service Principal with `Monitoring Reader` role.

## Quick start

```bash
export AZURE_SUBSCRIPTION_ID=<your-azure-subscription-id>
export KUBECONTEXT=<your-kubecontext>
export KFUSE_NAMESPACE=<your-kloudfuse-namespace>
export KLOUDFUSE_URL=https://<kloudfuse-hostname>
export KLOUDFUSE_SA_TOKEN=<your-kloudfuse-sa-token>

bash setup.sh
```

Apply the printed Helm values to `custom-values.yaml` and run a Helm upgrade. After ~5 minutes, search for `azure.` in Kloudfuse Metrics Explorer.

## Teardown

```bash
export AZURE_SUBSCRIPTION_ID=<your-azure-subscription-id>
export KUBECONTEXT=<your-kubecontext>
export KFUSE_NAMESPACE=<your-kloudfuse-namespace>
bash teardown.sh
```

## What was pre-existing (as of 2026-07-14)

- A Service Principal with `Monitoring Reader` on the subscription may already exist; a new SP `kloudfuse-cloud-exporter` was created for this validation.
- The cloud exporter was present in the Helm chart but disabled (`cloud-exporter.enabled: false`).
- K8s secret `azure-cloud-exporter-credentials` was created in the target namespace.
