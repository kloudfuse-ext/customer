# HTTP Check Integration using Cluster Checks in `kfuse-observability-agent`

This guide explains how to configure [Datadog HTTP Checks](https://docs.datadoghq.com/integrations/http_check/) as **cluster checks** using the `kfuse-observability-agent` section in kfuse `custom-values.yaml` 

Cluster checks allow you to monitor internal and external HTTP endpoints across your Kubernetes cluster from a centralized agent.

---

## Sample `values.yaml` change

Use the following configuration to enable HTTP checks via Datadog’s Cluster Agent:

```
kfuse-observability-agent:
  datadog:
    datadog:
      clusterChecks:
        enabled: true

    clusterAgent:
      confd:
        http_check.yaml: |-
          init_config:

          instances:
            - name: Homepage Check
              url: https://example.com
              method: GET
              timeout: 3
              http_response_status_code: 200
              tags:
                - team:devops
                - env:prod

            - name: Internal Service Health
              url: http://my-service.namespace.svc.cluster.local:8080/health
              method: GET
              timeout: 5
              http_response_status_code: 200
              tags:
                - team:backend
                - env:staging

```

Post this configuration, upgrade the kfuse release with steps in upgrade [documentation](https://docs.kloudfuse.com/platform/latest/upgrade/)

## Post Upgrade
### Verifying the HTTP Check
#### Get the Datadog Cluster Agent pod name:
  ```
  kubectl get pods -l app=kfuse-observability-agent-cluster-agent -n kfuse
  ```

#### Exec into the Cluster Agent
  ```
  kubectl exec -it <cluster-agent-pod-name> -n kfuse -- agent status
  ```

#### Look for the http_check section
```
Checks
  http_check
    - Instance ID: ...
      URL: https://example.com
      Status: UP
```

### Metrics Available in Kloudfuse for creating alerts/dashboards 

Navigate to Metrics -> Summary on Kloudfuse UI and you can view the following metrics for the endpoints added in `http_check`

- `network_http_can_connect`

- `network_http_cant_connect`

- `network_http_response_time`

Reach out to Kloudfuse Customer Success team for any additional queries.
