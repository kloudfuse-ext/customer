# Agent Network Failure Behavior

This document explains how the Agent behaves when it cannot send telemetry to the backend (e.g., during a network outage or server failure). It also details the resource consumption controls and relevant configuration settings.

## Overview

When the Agent fails to send data to the servers, it prioritizes **system stability** (protecting memory and CPU) over data preservation. It enters a "Retry Mode" where it buffers data in memory up to a configurable limit.

- **Buffering:** Failed requests are stored in a memory buffer (Retry Queue).
- **Dropping Data:** Once the memory buffer is full, the Agent **drops the oldest and lowest-priority data** to make room for new data. It does *not* grow memory usage indefinitely.
- **Throttling:** The Agent uses an exponential backoff strategy to avoid overwhelming the network or CPU.

## Resource Consumption

| Resource | Behavior during failure | Limits |
| :--- | :--- | :--- |
| **Memory** | Increases until the configured limit is reached, then plateaus. | Defaults to **~15 MB** of payload data. |
| **CPU** | Remains low. Uses exponential backoff (sleeping) between retries. | Minimal CPU overhead for queue management. |
| **Disk** | **Zero** usage by default. | Disk buffering is disabled unless explicitly configured. |

## Data Reliability Details

The Agent differentiates between transaction priorities and uses a specific strategy when the buffer fills up:

1.  **Retry Queue:** Stores failed transactions.
2.  **Drop Strategy:** When the queue exceeds `forwarder_retry_queue_payloads_max_size`:
    *   It sorts transactions by Priority (Low vs. High) and Creation Time.
    *   It removes (drops) **Low Priority** and **Oldest** transactions first.
    *   This ensures that if connectivity is restored, the most recent and important data is sent.
3.  **Persistence:** If the Agent is restarted, **buffered data in memory is lost** unless disk storage is enabled.

## Configuration Reference

The following settings control the Forwarder's behavior. These can be set in yaml or via environment variables.

### Memory & Buffering

| Setting / Env Var | Default | Description |
| :--- | :--- | :--- |
| `forwarder_retry_queue_payloads_max_size`<br>`DD_FORWARDER_RETRY_QUEUE_PAYLOADS_MAX_SIZE` | `15,728,640` (15 MB) | The maximum amount of memory (in bytes) allocated for the retry queue. <br>**Note:** This counts payload size only, actual RAM usage will be slightly higher due to overhead. |

### Disk Persistence (Optional)

By default, the Agent does not use disk for retries. Enable this to survive restarts or buffer more data.

| Setting / Env Var | Default | Description |
| :--- | :--- | :--- |
| `forwarder_storage_max_size_in_bytes`<br>`DD_FORWARDER_STORAGE_MAX_SIZE_IN_BYTES` | `0` (Disabled) | Maximum disk space to use for retry queue. Set to a positive value (e.g., `536870912` for 512MB) to enable. |
| `forwarder_storage_path`<br>`DD_FORWARDER_STORAGE_PATH` | `$(run_path)/transactions_to_retry` | The directory where retry files are stored. |
| `forwarder_storage_max_disk_ratio`<br>`DD_FORWARDER_STORAGE_MAX_DISK_RATIO` | `0.80` (80%) | The Agent will stop writing to disk if the host's disk usage exceeds this ratio. |

### Network & Concurrency

| Setting / Env Var | Default | Description |
| :--- | :--- | :--- |
| `forwarder_num_workers`<br>`DD_FORWARDER_NUM_WORKERS` | `1` | Number of concurrent workers sending data to the backend. |
| `forwarder_max_concurrent_requests`<br>`DD_FORWARDER_MAX_CONCURRENT_REQUESTS` | `10` | Maximum number of concurrent HTTP requests *per worker*. |
| `forwarder_timeout`<br>`DD_FORWARDER_TIMEOUT` | `20` (seconds) | Timeout for individual HTTP network requests. |

### Backoff Strategy (Exponential)

These settings control how long the Agent waits before retrying a failed endpoint.

| Setting / Env Var | Default | Description |
| :--- | :--- | :--- |
| `forwarder_backoff_base`<br>`DD_FORWARDER_BACKOFF_BASE` | `2` | The base base for the exponential backoff calculation. |
| `forwarder_backoff_factor`<br>`DD_FORWARDER_BACKOFF_FACTOR` | `2` | The factor by which the wait time increases after each failure. |
| `forwarder_backoff_max`<br>`DD_FORWARDER_BACKOFF_MAX` | `64` (seconds) | The maximum time the Agent will wait between retries. |
| `forwarder_recovery_interval`<br>`DD_FORWARDER_RECOVERY_INTERVAL` | `2` (seconds) | Interval to reset the error count after a successful connection. |

## Code Implementation References

For developers interested in the internal implementation, here are the links to the core logic in the `datadog-agent` repository:

### Buffering & Dropping
*   **Retry Queue Logic (`transaction_retry_queue.go`):**
    *   [Add Method](https://github.com/DataDog/datadog-agent/blob/main/comp/forwarder/defaultforwarder/internal/retry/transaction_retry_queue.go#L107): Handles adding transactions to the queue and triggers dropping if the memory limit is exceeded.
    *   [Dropping Logic](https://github.com/DataDog/datadog-agent/blob/main/comp/forwarder/defaultforwarder/internal/retry/transaction_retry_queue.go#L243): `extractTransactionsFromMemory` implements the removal of transactions (sorted by priority) when the buffer is full.

### Throttling & Backoff
*   **Circuit Breaker (`blocked_endpoints.go`):**
    *   [Backoff Implementation](https://github.com/DataDog/datadog-agent/blob/main/comp/forwarder/defaultforwarder/blocked_endpoints.go#L112): The `close` method is called on error, incrementing the error count and calculating the next retry time using the exponential backoff policy.
    *   [Initialization](https://github.com/DataDog/datadog-agent/blob/main/comp/forwarder/defaultforwarder/blocked_endpoints.go#L66): Sets up the `ExpBackoffPolicy` with the configured base and max/min values.

### Retry Loop
*   **Domain Forwarder (`domain_forwarder.go`):**
    *   [Retry Loop](https://github.com/DataDog/datadog-agent/blob/main/comp/forwarder/defaultforwarder/domain_forwarder.go#L89): The `retryTransactions` function is called periodically to check for blocked endpoints and attempt to resend transactions from the queue.

## Documentation Links

*   **Datadog Agent Documentation:** [https://docs.datadoghq.com/agent/](https://docs.datadoghq.com/agent/)
*   **Network Traffic Guide:** [https://docs.datadoghq.com/agent/guide/network/](https://docs.datadoghq.com/agent/guide/network/)
*   **Agent Configuration Files:** [https://docs.datadoghq.com/agent/guide/agent-configuration-files/](https://docs.datadoghq.com/agent/guide/agent-configuration-files/)
