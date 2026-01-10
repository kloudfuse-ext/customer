# Stop Queries and Ingestion

## Stop Queries

To stop queries, stop corresponding query service pods. As an example, to stop logs queries, run below command.

```bash
kubectl scale sts -n kfuse logs-query-service --replicas=0
```

## Cancel Currently Running API Calls

To cancel currently running api calls, you could bounce the pods instead of scaling them down:

```bash
kubectl rollout restart sts -n kfuse logs-query-service
```

## Stop Ingestion

Drop all packets at the ingress. This will drop and acknowledge success (so clients/agents don't retry/complain).

```bash
kubectl patch ingress kfuse-ingest --type=json -p='[{"op": "replace", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1rewrite-target", "value": "/api/v1/drop"}]'
```

### Restore Ingestion

To restore the correct value back, run below command:

```bash
kubectl patch ingress kfuse-ingest --type=json -p='[{"op": "replace", "path": "/metadata/annotations/nginx.ingress.kubernetes.io~1rewrite-target", "value": "/$2$3"}]'
```

