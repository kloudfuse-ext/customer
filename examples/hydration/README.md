# Hydration API Examples

The Kloudfuse hydration service replays archived log files back into Kloudfuse for analysis.
All endpoints are available at `https://<your-instance>/hydration/query/`.

Replace `<your-instance>` with your Kloudfuse hostname and `<sa-token>` with a valid Service Account token.

---

## List available archives

```bash
curl -H "Authorization: Bearer <sa-token>" \
     "https://<your-instance>/hydration/query/list-archives"
```

**Response**

```json
[
  { "name": "k8s-production" },
  { "name": "k8s-staging" },
  { "name": "payment-service" }
]
```

---

## Submit a hydration job — all logs in a time range

Hydrate every log line in a 24-hour window with no filtering.

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/hydrate" \
     -d '{
       "archiveName": "k8s-production",
       "startTsMs": 1720000000000,
       "endTsMs":   1720086400000
     }'
```

**Response**

```json
{ "jobId": "550e8400-e29b-41d4-a716-446655440000" }
```

---

## Submit a hydration job — filter by label

Hydrate only `error`-level logs from the `payment-service`.
Multiple filters are combined with logical AND.

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/hydrate" \
     -d '{
       "archiveName": "k8s-production",
       "startTsMs": 1720000000000,
       "endTsMs":   1720086400000,
       "filters": [
         { "field": "service", "operation": "eq", "value": "payment-service", "type": "labels" },
         { "field": "level",   "operation": "eq", "value": "error",           "type": "labels" }
       ]
     }'
```

---

## Submit a hydration job — filter by message content

Hydrate logs whose raw message contains "connection refused".

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/hydrate" \
     -d '{
       "archiveName": "k8s-production",
       "startTsMs": 1720000000000,
       "endTsMs":   1720086400000,
       "filters": [
         { "operation": "contains", "value": "connection refused", "type": "message" }
       ]
     }'
```

---

## Submit a hydration job — filter by regex on a label

Hydrate logs from any namespace matching the pattern `prod-.*`.
Regex patterns are anchored to the full field value.

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/hydrate" \
     -d '{
       "archiveName": "k8s-production",
       "startTsMs": 1720000000000,
       "endTsMs":   1720086400000,
       "filters": [
         { "field": "namespace", "operation": "regex", "value": "prod-.*", "type": "labels" }
       ]
     }'
```

---

## Dry run — count matching lines without replaying

Set `isDryRun: true` to see how many lines would be replayed before committing.

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/hydrate" \
     -d '{
       "archiveName": "k8s-production",
       "startTsMs": 1720000000000,
       "endTsMs":   1720086400000,
       "isDryRun": true,
       "filters": [
         { "field": "level", "operation": "neq", "value": "debug", "type": "labels" }
       ]
     }'
```

---

## Check job progress

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/job-progress" \
     -d '{ "jobId": "550e8400-e29b-41d4-a716-446655440000" }'
```

**Response**

```json
{
  "jobId":      "550e8400-e29b-41d4-a716-446655440000",
  "jobStatus":  "HYDRATING",
  "jobSummary": "{\"totalHours\":24,\"completedHours\":6,\"totalLines\":0,\"filteredLines\":0}"
}
```

Job status values: `INIT`, `HYDRATING`, `PAUSED`, `DONE`, `FAILED`, `CANCELED`.

---

## List recent jobs

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/list-jobs" \
     -d '{ "count": 10 }'
```

---

## Pause a running job

Only jobs in `HYDRATING` status can be paused.

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/pause" \
     -d '{ "jobId": "550e8400-e29b-41d4-a716-446655440000" }'
```

---

## Resume a paused job

Only jobs in `PAUSED` status can be resumed.

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/resume" \
     -d '{ "jobId": "550e8400-e29b-41d4-a716-446655440000" }'
```

---

## Cancel a job

Jobs in `DONE` or `FAILED` status cannot be canceled.

```bash
curl -H "Authorization: Bearer <sa-token>" \
     -H "Content-Type: application/json" \
     -X POST "https://<your-instance>/hydration/query/cancel" \
     -d '{ "jobId": "550e8400-e29b-41d4-a716-446655440000" }'
```

---

## Filter operations reference

| Operation | Description |
|---|---|
| `eq` | Exact match |
| `neq` | Not equal |
| `contains` | Substring present |
| `ncontains` | Substring absent |
| `regex` | Full-value regex match (anchored) |
| `nregex` | Full-value regex does not match (anchored) |

Filter `type` values: `labels` (matches label map and agent-extracted facets), `message` (matches raw log message).
