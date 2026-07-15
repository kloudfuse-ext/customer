# Azure Logs → Kloudfuse

Validates the Azure log integration documented at `data-collection/cloud-services/azure/logs.adoc`.

Logs flow: Azure resources → Event Hub → Function App → Kloudfuse `/api/v2/logs`

## Quick start

```bash
export AZURE_SUBSCRIPTION_ID=<your-azure-subscription-id>
export KLOUDFUSE_URL=https://<kloudfuse-hostname>
export KLOUDFUSE_SA_TOKEN=<your-kloudfuse-sa-token>

bash setup.sh
```

## Teardown

```bash
export AZURE_SUBSCRIPTION_ID=<your-azure-subscription-id>
export RESOURCE_GROUP=kloudfuse-logs-rg
bash teardown.sh
```

## What was pre-existing (as of 2026-07-14)

- Function App `Kfuse-AzureFunction` (Canada Central) in `Kfuse-AzureFunction_group` already existed with `EventHubTrigger1` enabled, pointing at the `kfusemonitorlogs` Event Hub namespace / `kfusemonitor` hub.
- Subscription-level diagnostic setting `kfuse-diagnostic-setting` was already routing activity logs to that hub.
- The Function App was updated to point at the target Kloudfuse instance by setting `KF_URL` and `KF_API_KEY` app settings.
- The `setup.sh` creates fresh infrastructure under a dedicated resource group (`kloudfuse-logs-rg`) for reproducibility.
