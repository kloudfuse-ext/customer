# High Drop Rate from Rate Control

## Table of Contents

- [Summary](#summary)
- [Symptoms](#symptoms)
- [Step 1: Identify the Affected Stream and Class](#step-1-identify-the-affected-stream-and-class)
- [Step 2: Check Current Drop and Allowed Rates](#step-2-check-current-drop-and-allowed-rates)
- [Step 3: Review the Configured Rate Limit](#step-3-review-the-configured-rate-limit)
- [Step 4: Diagnose Root Cause](#step-4-diagnose-root-cause)
- [Step 5: Remediation](#step-5-remediation)
- [Step 6: Post-Recovery Verification](#step-6-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

Kloudfuse Rate Control enforces per-stream, per-class ingestion limits to protect the platform from excessive data volumes. When the ingestion rate for a stream exceeds its configured limit, events are dropped. This alert fires when the drop rate becomes a significant proportion of the allowed rate — indicating that a meaningful volume of customer data is being lost due to rate limiting.

**Impact:** Events being dropped by rate control are permanently lost and will not appear in Kloudfuse. Depending on the stream, this may cause gaps in metrics, missing log lines, incomplete traces, or dropped RUM events.

**Common Root Causes:**
- A sudden spike in data volume from a new source (e.g., new application deployment, increased logging verbosity)
- A misconfigured rate limit that is set too low for the actual ingestion volume
- A class configured as an intentional drop rule (expected behavior — see Note below)
- A burst of data following a service restart or backfill

**Note on intentional drop classes:** Rate control classes can be configured to intentionally drop data (e.g., to exclude specific metric namespaces or log sources). If the alerting class is a configured drop rule, no action is required. Review the class name and its configuration in the Kloudfuse Admin → Rate Control UI before escalating.

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

**External Documentation:**
- [Rate Control Overview](https://docs.kloudfuse.com/platform/latest/data-management/routing/rate-control/)
- [Logs Rate Control](https://docs.kloudfuse.com/platform/latest/data-management/routing/rate-control-logs/)
- [Metrics Rate Control](https://docs.kloudfuse.com/platform/latest/data-management/routing/rate-control-metrics/)
- [Traces Rate Control](https://docs.kloudfuse.com/platform/latest/data-management/routing/rate-control-traces/)
- [Events Rate Control](https://docs.kloudfuse.com/platform/latest/data-management/routing/rate-control-events/)
- [RUM Rate Control](https://docs.kloudfuse.com/platform/latest/data-management/routing/rate-control-rum/)

---

## Symptoms

### Alert Expression

```promql
(
  sum by (org_id, kube_cluster_name, stream, class)(
    rate(ingester_rate_control_num_events_dropped_count{kfuse="true", class!="kfuse_cp_class"}[5m])
  )
/
  sum by (org_id, kube_cluster_name, stream, class)(
    rate(ingester_rate_control_num_events_allowed_count{kfuse="true", class!="kfuse_cp_class"}[5m])
  )
) * 100
and on (org_id, kube_cluster_name, stream, class)
(
  sum by (org_id, kube_cluster_name, stream, class)(
    rate(ingester_rate_control_num_events_allowed_count{kfuse="true", class!="kfuse_cp_class"}[5m])
  ) > 100
)
```

The alert fires when dropped events exceed **20% of allowed events**, provided the allowed rate is at least **5,000 events/second**. The minimum allowed rate threshold of 5,000 events/second prevents false positives from low-volume streams where even a handful of drops would produce a large percentage. At this threshold, the alert will only fire when at least 1,000 events/second are actively being dropped.

### Metrics Indicating Issue

| Metric | Description |
|--------|-------------|
| `ingester_rate_control_num_events_dropped_count` | Counter of events dropped by rate control (by org, stream, class) |
| `ingester_rate_control_num_events_allowed_count` | Counter of events allowed through (by org, stream, class) |
| `ingester_rate_control_configured_rate` | The configured rate limit ceiling (events/sec, by org, stream, class) |

**Key labels:** `org_id`, `kube_cluster_name`, `stream` (metrics, logs, traces, rum, events), `class` (rate control policy class name)

---

## Step 1: Identify the Affected Stream and Class

The alert labels `stream` and `class` identify the affected rate control policy. Note both values — they are used throughout this runbook.

Check current drop rates across all streams and classes:

```promql
sum by (org_id, kube_cluster_name, stream, class)(
  rate(ingester_rate_control_num_events_dropped_count{kfuse="true", class!="kfuse_cp_class"}[5m])
)
```

Check the drop-to-allowed ratio (percentage):

```promql
(
  sum by (org_id, kube_cluster_name, stream, class)(
    rate(ingester_rate_control_num_events_dropped_count{kfuse="true", class!="kfuse_cp_class"}[5m])
  )
/
  sum by (org_id, kube_cluster_name, stream, class)(
    rate(ingester_rate_control_num_events_allowed_count{kfuse="true", class!="kfuse_cp_class"}[5m])
  )
) * 100
```

---

## Step 2: Check Current Drop and Allowed Rates

Check the actual event rates for the affected `org_id`, `stream`, and `class`:

**Allowed rate (events/sec over the last 5 minutes):**

```promql
sum by (org_id, kube_cluster_name, stream, class)(
  rate(ingester_rate_control_num_events_allowed_count{
    kfuse="true",
    org_id="<ORG_ID>",
    stream="<STREAM>",
    class="<CLASS>"
  }[5m])
)
```

**Drop rate (events/sec over the last 5 minutes):**

```promql
sum by (org_id, kube_cluster_name, stream, class)(
  rate(ingester_rate_control_num_events_dropped_count{
    kfuse="true",
    org_id="<ORG_ID>",
    stream="<STREAM>",
    class="<CLASS>"
  }[5m])
)
```

Compare the two rates. A sustained drop rate that is a large fraction of the allowed rate indicates the ingestion volume is consistently hitting the configured rate limit.

---

## Step 3: Review the Configured Rate Limit

Check the configured rate limit for the affected stream and class:

```promql
ingester_rate_control_configured_rate{
  kfuse="true",
  org_id="<ORG_ID>",
  stream="<STREAM>",
  class="<CLASS>"
}
```

**Navigate to:** Kloudfuse UI → **Admin** → **Rate Control**

Review the current policy for the affected stream and class. Check:
- **Ingestion Rate** — the maximum events/second allowed
- **Ingestion Rate** — the sustained maximum events/second for this stream; divided equally across all ingester replicas
- **Burst** — the maximum number of events that can be ingested in a single spike; also divided across replicas and then distributed proportionally across classes. See [Burst Configuration](#burst-configuration) in Step 5 for guidance on setting this value
- **Drop Percentage (1h)** — the historical drop percentage displayed in the UI

If the current `allowed_rate` is close to the `configured_rate`, the ingestion volume is legitimately exceeding the limit.

---

## Step 4: Diagnose Root Cause

### Case A: Intentional Drop Class

If the class name suggests it is a configured drop rule (e.g., a class named `DropAirflowMetrics`, `BlockedSources`, or similar), this is expected behavior. The alert can be suppressed for this class by adding a `class!="<CLASS_NAME>"` exclusion to the alert expression, or by reviewing whether the drop rule is still needed.

### Case B: Traffic Spike from a New Source

Check whether a new application, service, or deployment is sending unexpected data volume. Look for recent changes in the ingestion rate trend:

```promql
sum by (org_id, stream, class)(
  rate(ingester_rate_control_num_events_allowed_count{
    kfuse="true",
    org_id="<ORG_ID>",
    stream="<STREAM>",
    class="<CLASS>"
  }[5m])
)
```

View over time to see when the volume increase started.

### Case C: Rate Limit Set Too Low

If the ingestion volume is legitimate and the drops represent real data loss, the rate limit may need to be increased. Consider the business impact of losing events at the current drop rate before increasing the limit.

### Case D: Backfill or Service Restart Burst

A temporary burst following a service restart or log backfill will resolve on its own. If the drop rate returns to normal within 15–30 minutes, no action may be needed. Monitor until the burst subsides.

---

## Step 5: Remediation

### Burst Configuration

Before increasing the sustained rate limit, consider whether the drops are caused by a short-lived spike that the burst setting could absorb.

**How burst works:** The `Burst` value is the maximum number of events that can be accepted in a single instantaneous spike. Internally, the total burst is divided equally across all ingester replicas, and then each replica distributes its share proportionally across classes. This means a burst of `5000` across 5 replicas gives each ingester a burst of `1000`.

**Burst size recommendations:**

| Goal | Formula | Example (rate=10,000/sec) |
|------|---------|--------------------------|
| Absorb up to 1 second of excess traffic | `burst = rate` | `burst = 10000` |
| Absorb up to N seconds of excess traffic | `burst = rate × N` | `burst = 30000` (3 seconds) |

**Navigate to:** Kloudfuse UI → **Admin** → **Rate Control** → select the affected stream → update **Burst**

If drops are occurring only during brief spikes (e.g., Case D: service restart or backfill), increasing burst is often the right fix without changing the sustained rate. For stream-specific defaults and guidance, see the [External Documentation](#summary) links.

### Increase the Sustained Rate Limit

If the traffic is legitimate and consistently exceeds the limit (not just burst spikes):

**Navigate to:** Kloudfuse UI → **Admin** → **Rate Control** → select the affected stream

Increase the **Ingestion Rate** to accommodate the actual volume. A safe starting point is 1.5× the current allowed rate. Update **Burst** proportionally using the formula above.

### Reduce the Ingestion Volume

If the traffic is unexpectedly high:

- Identify the source generating excess data (check `pod_name`, `kube_namespace`, or `kube_service` labels on the ingested data)
- Reduce logging verbosity, metric cardinality, or sampling rate at the source
- Add a targeted drop rule for the noisy source as a temporary measure

### Add a Class-Specific Drop Rule

If specific data is intentionally unwanted, configure a dedicated rate control class with a drop rate of 0:

**Navigate to:** Kloudfuse UI → **Admin** → **Rate Control** → **Add Rate Control**

---

## Step 6: Post-Recovery Verification

Verify the drop rate has returned to an acceptable level:

```promql
(
  sum by (org_id, kube_cluster_name, stream, class)(
    rate(ingester_rate_control_num_events_dropped_count{
      kfuse="true",
      org_id="<ORG_ID>",
      stream="<STREAM>",
      class="<CLASS>"
    }[5m])
  )
/
  sum by (org_id, kube_cluster_name, stream, class)(
    rate(ingester_rate_control_num_events_allowed_count{
      kfuse="true",
      org_id="<ORG_ID>",
      stream="<STREAM>",
      class="<CLASS>"
    }[5m])
  )
) * 100
```

Result should be below 20%. Confirm in the Kloudfuse Admin → Rate Control UI that the **Drop Percentage (1h)** is trending down.

---

## Prevention

### Monitor Drop Percentage Proactively

Track the overall drop rate across all streams:

```promql
sum by (org_id, stream)(
  rate(ingester_rate_control_num_events_dropped_count{kfuse="true", class!="kfuse_cp_class"}[5m])
)
```

### Set Rate Limits with Headroom

Configure rate limits at 2× the expected peak volume to absorb bursts without dropping. Use `burst = rate` as a baseline.

### Review Drop Rules Periodically

Audit intentional drop classes regularly to ensure they still reflect current data routing requirements. Remove or update stale rules that may be masking unexpected data sources.

---

## Related Runbooks

- [Degraded Deployments](../degraded_deployments.md) — Ingester pod degradation that may reduce effective throughput capacity
- [CrashLoopBackOff Alert](../crashloopbackupoff_alert.md) — Ingester pods crash-looping, which reduces replica count and lowers the effective burst and rate limits
