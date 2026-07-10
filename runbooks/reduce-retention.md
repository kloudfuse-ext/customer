# Reduce Retention and Reclaim Storage

## Summary

This runbook covers how to **reduce the retention period** for a Kloudfuse data stream
(logs, events, traces, metrics) and reclaim the disk (PVC) and blob-storage space that
the now out-of-retention data was using.

Lowering the retention policy in the values yaml applies to **new data** going forward. To
clean up older data that is already past the new window, we need to manually delete it using
[`scripts/delete_pinot_segments_older_days.sh`](../scripts/delete_pinot_segments_older_days.sh).

**Note:** All commands assume namespace `kfuse`. If your deployment uses a different
namespace, replace `kfuse` accordingly.

> **Order matters.** Always apply the yaml retention change (Step 1) *before* deleting
> segments (Step 2). If you delete segments while the old (longer) retention is still
> configured, Pinot may re-fetch or the change won't stick as expected.

---

## Data stream → Pinot table mapping

The `retentionPolicy` keys in the values yaml map to Pinot tables as follows:

| Retention stream | Pinot base table | Table used by script (`_REALTIME`) |
| ---------------- | ---------------- | ---------------------------------- |
| `logs`           | `kf_logs`        | `kf_logs_REALTIME`                 |
| `events`         | `kf_events`      | `kf_events_REALTIME`               |
| `traces`         | `kf_traces`      | `kf_traces_REALTIME`               |
| `metrics`        | `kf_metrics`     | `kf_metrics_REALTIME`              |

---

## Step 1: Change the retention policy in the values yaml

Edit the customer values yaml and set the desired
retention under `retentionPolicy`. `retentionTimeValue` is the number of `retentionTimeUnit`
(`DAYS`) to keep.

```yaml
retentionPolicy:
  logs:
    default:
      retentionTimeUnit: "DAYS"
      retentionTimeValue: 8
  events:
    default:
      retentionTimeUnit: "DAYS"
      retentionTimeValue: 4
  traces:
    default:
      retentionTimeUnit: "DAYS"
      retentionTimeValue: 8
  metrics:
    default:
      retentionTimeUnit: "DAYS"
      retentionTimeValue: 8
```

Apply the change with a `helm upgrade` using the **same chart version** currently installed
(so you don't accidentally trigger a software upgrade alongside the retention change):

```bash
# Verify the currently installed version first
helm ls -n kfuse

# Apply, pinning the same version returned above
helm upgrade kfuse kfuse/kfuse -n kfuse \
  --version <CURRENT_VERSION> \
  -f artifacts/aws/prod-aws.yaml
```

Commit the yaml change so the cluster state stays reflected in the customer repo.

---

## Step 2: Delete out-of-retention segments from disk and blob storage

Reducing retention does not immediately reclaim space. Use the script to force-delete
segments whose end time is older than the new retention window.

The controller must be reachable at `localhost:9000`, so port-forward to it in a separate
terminal (leave it running):

```bash
kubectl port-forward -n kfuse svc/pinot-controller 9000:9000
```

Create a working directory per table so the status files the script writes are kept
together:

```bash
mkdir -p ~/retention-cleanup/kf_logs && cd ~/retention-cleanup/kf_logs
```

### 2a. Dry run first (always)

List what *would* be deleted without deleting anything. Set `-d` to your **new** retention
value (or slightly higher for safety margin):

```bash
/path/to/customer/scripts/delete_pinot_segments_older_days.sh \
  --table kf_logs --days 8 --dry-run
```

Review the segment list it prints and saves to `kf_logs.old_segments.txt`. Confirm the
count and names look reasonable (e.g. only old segments, not consuming/recent ones).

### 2b. Delete

Once you've verified the dry-run output, delete. You can either re-run without `--dry-run`,
or feed the saved list back with `-f` (recommended — it deletes exactly what you reviewed):

```bash
# Option A: re-scan and delete (prompts before deleting)
/path/to/customer/scripts/delete_pinot_segments_older_days.sh --table kf_logs --days 8

# Option B: delete exactly the reviewed list
/path/to/customer/scripts/delete_pinot_segments_older_days.sh \
  --table kf_logs --file kf_logs.old_segments.txt
```

The script prompts for confirmation (press Enter to proceed, `^C` to cancel) and prints
each segment as it deletes it.

Repeat Step 2 for each stream you reduced (`kf_events`, `kf_traces`, `kf_metrics`).

> **Recovery window.** Deleted segments are not purged instantly. Pinot moves them to the
> **`KFDeleteSegment/` prefix in the deep store (blob storage)**, where they are retained
> for **1 day** before being permanently removed. If you delete something by mistake, you
> have a same-day window to recover it from that prefix before it is gone for good.

---

## Step 3: Verify space was reclaimed

### 3a. PVC usage — System dashboard

Open the **System** dashboard in the Kloudfuse UI and check the **PVC / disk usage**
panels for `pinot-server`. After deletion, used space should trend down as servers drop
the local copies of the deleted segments.

You can cross-check from the CLI:

```bash
# PVC objects and capacity
kubectl get pvc -n kfuse | grep pinot-server

# Actual disk usage inside a server pod's data volume
kubectl exec -n kfuse pinot-server-0 -- df -h /var/pinot/server/data
```

> It can take a few minutes for servers to release the space after the controller deletes
> the segments. If usage doesn't drop, confirm the segments are actually gone from the
> table (see [Verify Pinot table names](#appendix-verify-pinot-table-names) endpoints).

### 3b. Blob storage (deep store)

Confirm the segment objects are cleared from the deep store, and that the deleted copies
landed under `KFDeleteSegment/` (staged for 1 day) rather than lingering in the live path.

---

## Step 4: Shrink the PVC to reclaim the freed capacity

Deleting segments frees space *inside* the volume, but the PVC (and the underlying disk)
stays the same size. Once you have **verified in Step 3** that the data is actually gone and
usage has dropped, you can shrink the Pinot **offline** PVC to the smaller size.

Kubernetes does not support shrinking a PVC in place, so this is done by recreating the
StatefulSet and its PVCs at the new (smaller) size. The data is safe because Pinot
**re-hydrates segments automatically from blob storage (deep store)** once the servers come back up

> **Do this only for the OFFLINE table's servers.** Only proceed after Step 3 confirms the
> deletion; the segments must exist in the deep store for re-hydration to work. Do this
> during a low-traffic window.

1. **Set the new (smaller) offline PVC size in the values yaml.**

   Adjust the offline Pinot server storage size to the reduced value, e.g.:

   ```yaml
   pinot:
     server:
       offline:
         persistence:
           size: <NEW_SMALLER_SIZE>   # e.g. 500Gi
   ```

   > Confirm the exact key path in `values.yaml` for your chart version before editing.

2. **Delete the offline StatefulSet and its PVCs.**

   ```bash
   # Inspect the offline server sts and PVCs first
   kubectl get sts -n kfuse | grep pinot-server-offline
   kubectl get pvc -n kfuse -l component=server-offline

   # Delete the sts (orphan the pods so they don't block) then the PVCs
   kubectl delete sts -n kfuse pinot-server-offline 
   kubectl delete pvc -n kfuse -l component=server-offline
   ```

   > Double-check the sts name and PVC label selector on your cluster before deleting —
   > **do not** delete the realtime server PVCs. Deleting a PVC is destructive to the local
   > copy; re-hydration from the deep store is what makes this safe.

3. **Re-deploy with helm, without changing any other values.**

   Run the same `helm upgrade` as Step 1 (same chart version, same values file — now with the
   smaller offline size). This recreates the offline StatefulSet and provisions fresh PVCs at
   the new size:

   ```bash
   helm upgrade kfuse kfuse/kfuse -n kfuse \
     --version <CURRENT_VERSION> \
     -f artifacts/aws/prod-aws.yaml
   ```

4. **Wait for the offline servers to come up and re-hydrate.**

   Once the pods are `Running`, Pinot automatically pulls the segments back from blob storage
   onto the new (smaller) PVCs. Watch progress:

   ```bash
   kubectl get pods -n kfuse | grep pinot-server-offline
   kubectl get pvc -n kfuse | grep pinot-server-offline   # should show the new smaller size
   ```

   Verify on the **System** dashboard that the offline servers report healthy PVC usage at
   the new capacity, and that queries over the offline table return the expected data.

---

## Rollback / recovery

- **Same-day mistaken deletion:** recover the segment objects from the `KFDeleteSegment/`
  prefix in the deep store before the 1-day window elapses.
- **Retention set too low:** raise `retentionTimeValue` back up in the yaml and
  `helm upgrade` again. Note this only restores *future* retention — data already deleted
  (and past the `KFDeleteSegment/` window) cannot be recovered.

---