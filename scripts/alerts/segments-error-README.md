# segments-error.sh

Diagnose and recover unavailable or errored Apache Pinot segments in a Kubernetes environment.

## Requirements

- `kubectl` with access to the cluster
- `python3` on the local machine
- Pinot controller and broker pods running with labels `component=controller` / `component=broker`

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `NAMESPACE` | `kfuse` | Kubernetes namespace |
| `CONTROLLER_PORT` | `9000` | Pinot controller HTTP port |
| `BROKER_PORT` | `8099` | Pinot broker HTTP port |
| `DRY_RUN` | _(unset)_ | Set to any value to skip destructive operations |

## Commands

### `status [table]`

Summarises segment health. Without a table name, scans all tables and lists any with non-healthy segments. With a table name, shows a breakdown grouped by current state, ideal state, and recommended action.

```
./segments-error.sh status
NAMESPACE=kfuse ./segments-error.sh status kf_logs_REALTIME
```

Output columns when a table is specified:

| Column | Description |
|---|---|
| Current | Segment state reported by the server (external view) |
| Ideal | State the controller intends (ideal state) |
| Count | Number of segments in this state combination |
| Est. size | Total estimated size of affected segments |
| Resolve | Recommended action (see decision table below) |
| Notes | Orphaned partition numbers, if applicable |
| Date range | Oldest and newest segment timestamps in the group |

**Resolve actions:**

| Current | Ideal | Action | Meaning |
|---|---|---|---|
| any non-healthy | any | `remove` | Partition has no active Kafka consumer — orphaned |
| OFFLINE | OFFLINE | `rebalance` | Controller has no server assigned — run rebalance |
| OFFLINE | ONLINE/CONSUMING | `reload` | Server has the data but failed to load it |
| OFFLINE | CONSUMING | `reset` | REALTIME segment stuck in ERROR state |
| other | other | `investigate` | Manual investigation required |

### `diagnose <table>`

Shows the full external view (which server holds each non-healthy segment) grouped by server. Useful for identifying whether one server is responsible for all failures.

```
NAMESPACE=kfuse ./segments-error.sh diagnose kf_logs_REALTIME
```

### `reload <table> [segment]`

Reloads segments from deep store. If a segment name is given, reloads only that segment. Without a segment name, finds all non-healthy segments and reloads them one at a time (prompts for confirmation).

Use reload when: ideal state is ONLINE but the server reports OFFLINE — the server has the segment in deep store but failed to load it (e.g. after a crash or OOM).

```
NAMESPACE=kfuse ./segments-error.sh reload kf_logs_REALTIME
NAMESPACE=kfuse ./segments-error.sh reload kf_logs_REALTIME kf_logs__0__1234__20250101T0000Z
```

### `rebalance <table>`

Reassigns segments whose ideal state is OFFLINE to available servers and sets them back to ONLINE. The API accepts the base table name or the suffixed name — either works.

Use rebalance when: both ideal and external view show OFFLINE — the controller has no server assigned for the segment at all.

```
NAMESPACE=kfuse ./segments-error.sh rebalance kf_logs
NAMESPACE=kfuse ./segments-error.sh rebalance kf_logs_REALTIME
DRY_RUN=1 NAMESPACE=kfuse ./segments-error.sh rebalance kf_logs   # preview without changes
```

After confirming, the script polls every 30 seconds and prints the non-healthy count until it reaches zero or stabilises.

### `watch <table> [job_id]`

Tails the controller logs filtered to rebalance activity for the given table. Optionally filter to a specific rebalance job ID (printed by the `rebalance` command).

```
NAMESPACE=kfuse ./segments-error.sh watch kf_logs
NAMESPACE=kfuse ./segments-error.sh watch kf_logs f8479e62-eed3-41ea-9e2f-9a645b67b523
```

Press Ctrl-C to stop.

### `reset <table> <segment>`

Resets a REALTIME consuming segment that is stuck in ERROR state. This tells the controller to clear the error and re-send the segment to the server for re-consumption from Kafka.

> **Warning:** Reset can cause data duplication or loss if the Kafka offset is replayed. Only use this when Kafka still retains data for the segment's time range and the segment never successfully committed.

```
NAMESPACE=kfuse ./segments-error.sh reset kf_logs_REALTIME kf_logs__0__1234__20250101T0000Z
```

### `remove <table> [--orphaned | segment]`

Three modes:

**Remove orphaned segments** — deletes segments whose Kafka partition no longer has an active consumer (i.e. the topic was scaled down). Detects orphaned partitions by finding partitions with no CONSUMING segment.

```
NAMESPACE=kfuse ./segments-error.sh remove kf_logs_REALTIME --orphaned
DRY_RUN=1 NAMESPACE=kfuse ./segments-error.sh remove kf_logs_REALTIME --orphaned
```

**Remove a single named segment** — deletes one specific segment from the ideal state.

```
NAMESPACE=kfuse ./segments-error.sh remove kf_logs_REALTIME kf_logs__0__1234__20250101T0000Z
```

**Remove segments missing from deep store** — finds non-healthy segments with `IN_PROGRESS` status (never committed to deep store) and deletes them from the ideal state.

```
NAMESPACE=kfuse ./segments-error.sh remove kf_logs_REALTIME
```

> **Warning:** All `remove` operations are permanent. The segment is removed from the Pinot ideal state and ZooKeeper. If the data is not in deep store it cannot be recovered. All modes prompt for confirmation unless `DRY_RUN` is set.

### `verify <table>`

Post-recovery check. Runs three checks:

1. External view health summary (total / healthy / non-healthy counts)
2. Broker query test (`SELECT COUNT(*)`) to confirm the table is queryable
3. PromQL queries to paste into Kloudfuse Metrics for ongoing monitoring

```
NAMESPACE=kfuse ./segments-error.sh verify kf_logs_REALTIME
```

## Typical recovery workflows

### Server crashed or OOM — segments OFFLINE but data is in deep store

```bash
# 1. Confirm: status shows Resolve=reload
NAMESPACE=kfuse ./segments-error.sh status kf_logs_REALTIME

# 2. Reload all non-healthy segments
NAMESPACE=kfuse ./segments-error.sh reload kf_logs_REALTIME

# 3. Verify recovery
NAMESPACE=kfuse ./segments-error.sh verify kf_logs_REALTIME
```

### Kafka topic scaled down — orphaned segments from removed partitions

```bash
# 1. Preview what would be removed
DRY_RUN=1 NAMESPACE=kfuse ./segments-error.sh remove kf_logs_REALTIME --orphaned

# 2. Remove orphaned segments
NAMESPACE=kfuse ./segments-error.sh remove kf_logs_REALTIME --orphaned

# 3. Verify
NAMESPACE=kfuse ./segments-error.sh verify kf_logs_REALTIME
```

### Segments OFFLINE in both ideal state and external view — controller lost assignments

```bash
# 1. Confirm: status shows Resolve=rebalance
NAMESPACE=kfuse ./segments-error.sh status kf_logs_REALTIME

# 2. Dry run first
DRY_RUN=1 NAMESPACE=kfuse ./segments-error.sh rebalance kf_logs

# 3. Run rebalance and monitor
NAMESPACE=kfuse ./segments-error.sh rebalance kf_logs

# 4. Watch controller logs in another terminal (optional)
NAMESPACE=kfuse ./segments-error.sh watch kf_logs

# 5. Verify
NAMESPACE=kfuse ./segments-error.sh verify kf_logs_REALTIME
```

### Segments stuck in ERROR and not in deep store — data lost, clean up ideal state

```bash
# 1. Check what's missing
NAMESPACE=kfuse ./segments-error.sh remove kf_logs_REALTIME   # shows missing list, prompts before deleting
```

## Notes

- REALTIME table names include a `_REALTIME` suffix (e.g. `kf_logs_REALTIME`). The `rebalance` command accepts either the suffixed or base name.
- `CONSUMING` is a healthy state for REALTIME tables — it means the segment is actively ingesting from Kafka.
- The controller pod is resolved once per invocation and cached for the session to avoid repeated `kubectl get pods` calls.
- Orphaned partition detection works by finding partitions with no active CONSUMING segment. If all consumers for a partition are stopped (not just missing), the partition may be falsely flagged as orphaned — verify with `status` before removing.
