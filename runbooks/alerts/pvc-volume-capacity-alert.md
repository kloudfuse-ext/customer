# PV Usage Above 90 Percent

## Table of Contents

- [Summary](#summary)
- [Symptoms](#symptoms)
- [Affected Services](#affected-services)
- [Step 1: Assess Urgency](#step-1-assess-urgency)
- [Step 2: Verify Current PVC Configuration](#step-2-verify-current-pvc-configuration)
- [Step 3: Expand the PVC](#step-3-expand-the-pvc)
- [Step 4: Verify the Expansion](#step-4-verify-the-expansion)
- [Step 5: Update values.yaml](#step-5-update-valuesyaml)
- [Step 6: Post-Recovery Verification](#step-6-post-recovery-verification)
- [Prevention](#prevention)
- [Vendor Notes](#vendor-notes)
- [Related Runbooks](#related-runbooks)

---

## Summary

When a Persistent Volume Claim (PVC) exceeds 90% capacity, the system is at risk of running out of disk space. A full PVC can cause the associated service to crash, stop ingesting data, or corrupt data in progress. This runbook provides steps to assess urgency and expand the PVC before it becomes critical.

**Impact:** Varies by service — see [Affected Services](#affected-services) below for service-specific impact.

**Common Root Causes:**
- Data volume growing faster than anticipated (ingestion rate increase, retention policy not enforced)
- PVC was sized too small at deployment time
- Log or temp file accumulation on the volume
- Pinot segment data not being cleaned up after compaction or retention expiry

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Symptoms

### Alert Expression

```promql
((
  max by (org_id, kube_cluster_name, kube_service, persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_used_bytes{kfuse="true", kf_node!=""}
  )
) * 100 /
(
  max by (org_id, kube_cluster_name, kube_service, persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_capacity_bytes{kfuse="true", kf_node!=""}
  )
)) > 90
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_kubelet_volume_stats_used_bytes / kubernetes_kubelet_volume_stats_capacity_bytes` | `< 90%` | `>= 90%` |

---

## Affected Services

The alert covers the following services. The `kube_service` label in the alert identifies which service is affected.

| Service | Component | Impact if PVC Fills                                                                                                                      |
|---------|-----------|------------------------------------------------------------------------------------------------------------------------------------------|
| `pinot-server-offline` | Pinot | Offline segment queries fail; segments cannot be downloaded from deep store; data loss risk                                              |
| `pinot-server-realtime` | Pinot | Realtime ingestion stops; consuming segments enter ERROR state; gap in logs/metrics/traces                                               |
| `pinot-controller` | Pinot | Controller loses ability to manage segment assignments; cluster coordination degrades                                                    |
| `pinot-minion` | Pinot | Background tasks (compaction, purge) fail; segment backlog grows                                                                         |
| `pinot-zookeeper` | Pinot | ZooKeeper loses ability to write transaction logs; Pinot cluster coordination fails entirely                                             |
| `kafka` | Kafka | Message ingestion stops; producers back-pressure; data loss if retention window exceeded                                                 |
| `kafka-kraft` | Kafka | KRaft controller loses metadata log; broker coordination fails                                                                           |
| `kafka-kraft-controller-headless` | Kafka | KRaft controller headless service volume fills; same impact as `kafka-kraft`                                                             |
| `kfuse-configdb` | Config DB | Configuration reads/writes fail; UI and API may become unavailable                                                                       |
| `kfuse-grafana` | Grafana | Dashboard and alert state loss; Grafana may fail to start                                                                                |
| `kfuse-profiler-server` | Profiler | Profiling data ingestion stops; profiler service may crash                                                                               |
| `kfuse-redis` | Redis | Cache writes fail; session data lost; API performance degrades                                                                           |
| `orchestrator-postgresql` | Orchestrator | Orchestrator database writes fail; job scheduling and state management stops and ingestion can be impacted is this manages rate control. |

---

## Step 1: Assess Urgency

| Usage | Action |
|-------|--------|
| 90–95% | Schedule expansion soon — monitor closely |
| 95–99% | Expand immediately — service disruption is imminent |
| 100% | Emergency — service is likely already degraded or crashed |

If the service is already failing due to a full disk, address the service impact first (restart the pod to clear temp files if possible), then proceed with expansion.

---

## Step 2: Verify Current PVC Configuration

Before resizing, verify the current configured size and compare it to what is deployed:

```bash
kubectl get pvc -n kfuse <PVC_NAME>
```

Also check the configured size in your `values.yaml` — for example, for `pinot-server-offline`:

```yaml
offline:
  persistence:
    size: 16500G
```

If the deployed size differs from `values.yaml`, investigate why before proceeding. The resize script will update both the PVC and the StatefulSet.

---

## Step 3: Expand the PVC

Use the [resize_pvc.sh](https://github.com/kloudfuse/customer/blob/main/scripts/alerts/resize_pvc.sh) script to resize the PVC and update the StatefulSet.

```bash
./resize_pvc.sh ${STATEFUL_SET} ${SIZE} ${KUBE_NAMESPACE}
```

The default namespace is `kfuse` if not specified.

**Example:**

```bash
./resize_pvc.sh pinot-server-offline 281Gi
```

The script will:
1. Patch the PVC with the new storage size
2. Save the existing StatefulSet YAML
3. Delete the StatefulSet with `--cascade=orphan` (pods continue running)
4. Apply an updated StatefulSet YAML with the new storage size

> **Note:** There are vendor-specific constraints on PVC resizing. Be aware of the limitations described in the [Vendor Notes](#vendor-notes) section before resizing, especially if you have recently resized the same volume.

---

## Step 4: Verify the Expansion

```bash
kubectl get pvc -n kfuse <PVC_NAME>
```

It may take up to a minute for all changes to complete. Verify the `CAPACITY` column reflects the new size.

Confirm the pod is healthy after the resize:

```bash
kubectl get pods -n kfuse | grep <STATEFUL_SET_NAME>
```

---

## Step 5: Update values.yaml

Update your `values.yaml` to reflect the new PVC size. If you skip this step, the next `helm upgrade` will fail with:

```
The PersistentVolumeClaim "<PVC_NAME>" is invalid: spec.resources.requests.storage: Forbidden: field can not be less than previous value
```

---

## Step 6: Post-Recovery Verification

Verify PV usage has dropped below the threshold:

```promql
(
  max by (org_id, kube_cluster_name, kube_service, persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_used_bytes{
      kfuse="true",
      persistentvolumeclaim="<PVC_NAME>"
    }
  )
) * 100 /
(
  max by (org_id, kube_cluster_name, kube_service, persistentvolumeclaim)(
    kubernetes_kubelet_volume_stats_capacity_bytes{
      kfuse="true",
      persistentvolumeclaim="<PVC_NAME>"
    }
  )
)
```

Result should be below 90. Confirm the affected service is operating normally by checking pod logs:

```bash
kubectl logs -n kfuse <POD_NAME> --tail=50
```

---

## Prevention

### Size PVCs With Growth Headroom

When provisioning, size PVCs with at least 30–40% headroom above the expected steady-state usage.

---

## Vendor Notes

### AWS

#### Elastic Volumes

[Request Amazon EBS volume modifications - Amazon EBS](https://docs.aws.amazon.com/ebs/latest/userguide/requesting-ebs-volume-modifications.html)

Keep the following in mind when modifying volumes:

> - After modifying a volume, **you must wait at least six hours** and ensure that the volume is in the in-use or available state before you can modify the same volume.
> - **Modifying an EBS volume can take from a few minutes to a few hours** depending on the configuration changes being applied.
> - **You can't cancel a volume modification request after it has been submitted.**
> - **You can only increase volume size. You can't decrease volume size.**
> - If you change the volume type from gp2 to gp3 without specifying IOPS or throughput, Amazon EBS automatically provisions equivalent performance to the source gp2 volume or the baseline gp3 performance, whichever is higher.

### GCP

#### Extreme Persistent Disks

[Extreme persistent disks | Compute Engine Documentation | Google Cloud](https://cloud.google.com/compute/docs/disks/extreme-persistent-disk)

**Note:** You can resize an Extreme Persistent Disk only once in a 6-hour period.

[Increase the size of a persistent disk | Compute Engine Documentation | Google Cloud](https://cloud.google.com/compute/docs/disks/resize-persistent-disk)

#### Resizing Persistent Volume Claim

[Using volume expansion | Google Kubernetes Engine (GKE) | Google Cloud](https://cloud.google.com/kubernetes-engine/docs/how-to/persistent-volumes/volume-expansion#using_volume_expansion)

**Note:** You will need to add `allowVolumeExpansion: true` to your StorageClass if it is not already set.

### Azure

#### Changing Performance Tier

[Change the performance of Azure managed disks - Azure Virtual Machines](https://learn.microsoft.com/en-us/azure/virtual-machines/disks-performance-tiers?tabs=azure-cli)

- Changing the performance tier is only supported for Premium SSD managed disks.
- Performance tiers of shared disks cannot be changed while attached to running VMs.
- A disk's performance tier can be downgraded only once every 12 hours.

#### Resizing Persistent Volume Claim

[Resize persistent volume claim (PVC) for Azure Arc-enabled data services volume - Azure Arc](https://learn.microsoft.com/en-us/azure/azure-arc/data/resize-persistent-volume-claim)

Resizing PVCs using this method only works if your StorageClass supports `AllowVolumeExpansion=True`.

---

## Related Runbooks

- [Pinot Segments Unavailable](pinot-segments-unavailable.md) — Pinot segment availability issues that may result from a full PVC
- [Pinot Segments in Error State](pinot-segments-in-error-state.md) — Pinot segment errors that may be caused by a full disk
- [CrashLoopBackOff Alert](crashloopbackupoff_alert.md) — Pod crash-looping, which may occur when a PVC is full
