# Kfuse User Access Service Availability

## Table of Contents

- [Summary](#summary)
- [Affected Components](#affected-components)
- [Symptoms](#symptoms)
- [Step 1: Identify the Affected Component](#step-1-identify-the-affected-component)
- [Step 2: Check Pod Status and Events](#step-2-check-pod-status-and-events)
- [Step 3: Check Logs for Root Cause](#step-3-check-logs-for-root-cause)
- [Step 4: Diagnose Root Cause](#step-4-diagnose-root-cause)
- [Step 5: Restart the Affected Component](#step-5-restart-the-affected-component)
- [Step 6: Post-Recovery Verification](#step-6-post-recovery-verification)
- [Prevention](#prevention)
- [Related Runbooks](#related-runbooks)

---

## Summary

The user access service availability alert fires when **1 or more** pods in the Kloudfuse user-facing tier become unavailable for **5 minutes**. This covers the UI, backend-for-frontend (beffe), authentication services, and management APIs. The threshold is tighter (5 minutes vs. 10 minutes for other services) because these components are directly user-facing — any unavailability is immediately visible.

**Impact:** Depending on the affected component:
- **ui:** The Kloudfuse web interface is inaccessible
- **beffe:** All UI API requests fail; the UI renders as blank or throws errors even if the UI pod is running
- **kfuse-auth:** Authentication fails; users cannot log in and existing sessions cannot be validated
- **kfuse-saml:** SAML SSO logins fail for organizations using SAML identity providers
- **kfuse-grafana:** The embedded Grafana instance is unavailable; Grafana dashboards and alerting rules cannot be accessed
- **user-mgmt-service:** User management operations (creating users, managing roles) are unavailable
- **config-mgmt-service:** Configuration management operations fail; alert and dashboard configurations cannot be saved or updated

**Common Root Causes:**
- Pod OOMKilled — UI and auth services are typically lightweight; OOM may indicate a misconfiguration or traffic spike
- Configuration database (`kfuse-configdb`) unavailable, causing auth/user-mgmt to fail on startup
- Node pressure causing pod eviction — see [Node condition not Ready](node_status.md)
- Certificate expiry causing kfuse-auth or kfuse-saml to reject connections
- Recent deployment introducing a startup crash

**Note:** All commands in this runbook assume namespace `kfuse`. If your deployment uses a different namespace, replace `kfuse` with your namespace in all commands.

---

## Affected Components

### Alert: Kfuse-user-access deployment pods are unavailable (Critical)
Fires when **1 or more** replicas are unavailable for **5 minutes**.

| Deployment | Role |
|------------|------|
| `beffe` | Backend-for-frontend — proxies and aggregates API calls for the UI |
| `ui` | Kloudfuse web application (React frontend) |
| `kfuse-grafana` | Embedded Grafana instance for dashboards and alerting |
| `kfuse-auth` | Authentication and session management service |
| `kfuse-saml` | SAML SSO identity provider integration |
| `user-mgmt-service` | User and role management API |
| `config-mgmt-service` | Alert, dashboard, and configuration management API |

---

## Symptoms

### Alert Expression

```promql
sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
  kubernetes_state_deployment_replicas_desired{
    kube_app_instance="kfuse",
    kube_deployment=~"beffe|ui|kfuse-grafana|kfuse-auth|kfuse-saml|user-mgmt-service|config-mgmt-service"
  }
) - sum by (org_id, kube_cluster_name, kube_namespace, kube_deployment)(
  kubernetes_state_deployment_replicas_available{
    kube_app_instance="kfuse",
    kube_deployment=~"beffe|ui|kfuse-grafana|kfuse-auth|kfuse-saml|user-mgmt-service|config-mgmt-service"
  }
) > 0
```

### Metrics Indicating Issue

| Metric | Healthy Value | Unhealthy Value |
|--------|--------------|-----------------|
| `kubernetes_state_deployment_replicas_desired - kubernetes_state_deployment_replicas_available` | `0` | `>= 1` |

### User-Visible Symptoms

| Symptom                                           | Likely Affected Component |
|---------------------------------------------------|--------------------------|
| Kloudfuse UI shows blank page or connection error | `ui` or `beffe` |
| Login page fails or shows "authentication error"  | `kfuse-auth` or `kfuse-saml` |
| SSO redirects fail                                | `kfuse-saml` |
| Grafana Dashboards are inaccessible               | `kfuse-grafana` |
| User/role management pages return 500 errors      | `user-mgmt-service` |
| Alert configuration changes fail to save          | `config-mgmt-service` |

---

## Step 1: Identify the Affected Component

The alert description will identify the specific `kube_deployment`. Check the alert details in the Kloudfuse UI or your notification channel.

List all user-access pods:

```bash
kubectl get pods -n kfuse | grep -E "beffe|^ui-|kfuse-grafana|kfuse-auth|kfuse-saml|user-mgmt|config-mgmt"
```

Look for pods in states other than `Running`:

| Pod State | Meaning |
|-----------|---------|
| `CrashLoopBackOff` | Container crashing on startup — check logs |
| `Pending` | Cannot be scheduled — check node capacity |
| `OOMKilled` | Memory limit exceeded |
| `ImagePullBackOff` | Image cannot be pulled — check image name and registry credentials |

---

## Step 2: Check Pod Status and Events

Describe the affected pod:

```bash
kubectl describe pod -n kfuse <POD_NAME>
```

Check the `Events` and `Containers` sections for:
- OOM kills
- Failed readiness/liveness probes
- Node assignment issues

Check namespace-wide events:

```bash
kubectl get events -n kfuse --sort-by='.lastTimestamp' | grep -E "Warning|Failed|OOM|Evict" | tail -20
```

---

## Step 3: Check Logs for Root Cause

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

Search for errors in the affected component:

```
kube_service="<DEPLOYMENT_NAME>" and level=~"error|fatal"
```

For authentication issues specifically:

```
kube_deployment=~"kfuse-auth|kfuse-saml" and ("failed" or "error" or "certificate" or "token" or "connection refused")
```

For logs from a pod that has already restarted, filter by time range in the Kloudfuse Logs Search UI to cover the window before the restart:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_pod="<POD_NAME>" and level=~"error|fatal"
```

Common error patterns:

| Log Pattern | Likely Cause |
|-------------|--------------|
| `connection refused` to configdb | `kfuse-configdb` is unavailable |
| `certificate has expired` | TLS certificate needs renewal |
| `SAML assertion validation failed` | SAML IDP configuration mismatch |
| `database connection pool exhausted` | DB connection limit reached |
| `OOMKilled` | Memory limit too low for current load |
| `panic:` or `runtime error:` | Application crash — check recent deployments |

---

## Step 4: Diagnose Root Cause

### Case A: beffe or ui Unavailable

The `beffe` (backend-for-frontend) is the primary API aggregator for the UI. If `beffe` is down, the UI will load but all data requests will fail, often showing a blank dashboard or spinner.

Check if `beffe` is reporting connection errors to upstream services:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="beffe" and ("connection refused" or "error" or "timeout" or "upstream")
```

Look for connection errors to downstream services like `kfuse-auth`, `query-service`, or `config-mgmt-service`.

The `ui` pod itself is a static file server — it rarely crashes. If it is down, check for image pull errors or resource pressure.

### Case B: kfuse-auth Unavailable

Authentication failures affect all users. Check if `kfuse-auth` can reach the `kfuse-configdb` (configuration database):

```bash
kubectl get pods -n kfuse | grep kfuse-configdb
```

If `kfuse-configdb` is down, see [Kfuse Misc Service Availability](kfuse-misc-service-availability.md).

Check for certificate expiry:

```bash
kubectl get secret -n kfuse | grep tls
kubectl describe secret -n kfuse <TLS_SECRET_NAME>
```

Review the `Not After` field on any TLS certificates used by `kfuse-auth`.

### Case C: kfuse-saml Unavailable

SAML failures only affect users using SSO. Check for:
- SAML metadata configuration errors
- Identity provider (IDP) connectivity issues
- Certificate expiry on the SAML signing certificate

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="kfuse-saml" and ("error" or "certificate" or "SAML" or "assertion" or "metadata")
```

### Case D: kfuse-grafana Unavailable

Grafana is used for dashboards and alert management. Check its PVC status — Grafana stores dashboard state on disk:

```bash
kubectl get pvc -n kfuse | grep grafana
```

If the PVC is full, follow the [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) runbook.

### Case E: user-mgmt-service or config-mgmt-service Unavailable

These management APIs depend on `kfuse-configdb`. If the configdb is unavailable, these services will fail on startup with database connection errors.

Check configdb health and pod status:

```bash
kubectl get pods -n kfuse | grep kfuse-configdb
```

Check configdb logs for startup failures:

**Navigate to:** Kloudfuse UI → **Logs** → **Advanced Search**

```
kube_service="kfuse-configdb" and level=~"error|fatal"
```

### Case F: Pod Stuck in Pending

```bash
kubectl describe pod -n kfuse <POD_NAME> | grep -A 10 "Events:"
```

If the node lacks capacity, check:

```bash
kubectl top nodes
kubectl describe nodes | grep -A 5 "Allocated resources"
```

---

## Step 5: Restart the Affected Component

After resolving the underlying cause, restart:

```bash
kubectl rollout restart deployment/<DEPLOYMENT_NAME> -n kfuse
kubectl rollout status deployment/<DEPLOYMENT_NAME> -n kfuse
```

For a single crashing pod:

```bash
kubectl delete pod -n kfuse <POD_NAME>
```

**Restart order if multiple user-access components are down:**
1. `kfuse-configdb` (if affected — see [Kfuse Misc Service Availability](kfuse-misc-service-availability.md))
2. `kfuse-auth`
3. `user-mgmt-service` and `config-mgmt-service`
4. `beffe`
5. `ui`, `kfuse-grafana`, `kfuse-saml`

---

## Step 6: Post-Recovery Verification

### Verify All Pods Are Running

```bash
kubectl get pods -n kfuse | grep -E "beffe|^ui-|kfuse-grafana|kfuse-auth|kfuse-saml|user-mgmt|config-mgmt"
```

All pods should show `Running` with all containers ready.

### Verify UI Access

Open the Kloudfuse UI in a browser and confirm:
1. The login page loads
2. Authentication succeeds (test with a known-good account)
3. Dashboards load correctly
4. Log, metrics, and trace search pages load

### Verify via PromQL

```promql
# Should return 0 for all deployments
sum by (kube_deployment)(
  kubernetes_state_deployment_replicas_desired{
    kube_app_instance="kfuse",
    kube_deployment=~"beffe|ui|kfuse-grafana|kfuse-auth|kfuse-saml|user-mgmt-service|config-mgmt-service"
  }
) - sum by (kube_deployment)(
  kubernetes_state_deployment_replicas_available{
    kube_app_instance="kfuse",
    kube_deployment=~"beffe|ui|kfuse-grafana|kfuse-auth|kfuse-saml|user-mgmt-service|config-mgmt-service"
  }
)
```

---

## Prevention

### Monitor Configuration Database Health

The `kfuse-configdb` is a shared dependency for `kfuse-auth`, `user-mgmt-service`, and `config-mgmt-service`. Monitor it separately and ensure its PVC has sufficient capacity.

### Set Up TLS Certificate Renewal

Configure automatic certificate renewal (cert-manager or equivalent) for all TLS certificates used by `kfuse-auth` and `kfuse-saml` to prevent expiry-related outages.

### Keep UI Components Lightweight

The `ui` and `beffe` pods should have relatively low resource requirements. If they are regularly OOMKilled, investigate for memory leaks or adjust limits to match observed usage:

```bash
kubectl top pods -n kfuse | grep -E "beffe|^ui-"
```

---

## Related Runbooks

- [Kfuse Misc Service Availability](kfuse-misc-service-availability.md) — Covers kfuse-configdb which is a dependency for auth/user-mgmt
- [PV Usage Above 90 Percent](pvc-volume-capacity-alert.md) — PVC full on Grafana or configdb
- [Node condition not Ready](node_status.md) — Node-level failures causing pod evictions
