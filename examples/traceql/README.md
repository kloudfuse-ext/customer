# TraceQL API Examples

Examples for searching Kloudfuse traces programmatically with **TraceQL**.
Kloudfuse serves TraceQL through the embedded Grafana's trace datasource
(`KfuseTraceDatasource`), so API calls go through the Grafana datasource
proxy rather than a public Tempo endpoint.

## Configuration

```bash
export KLOUDFUSE_HOST=<kloudfuse-hostname>
export KLOUDFUSE_TOKEN=glsa_...
# Find the trace datasource UID:
curl -s -H "Authorization: Bearer $KLOUDFUSE_TOKEN" \
  "https://$KLOUDFUSE_HOST/grafana/api/datasources" | \
  python3 -c "import json,sys; print([d['uid'] for d in json.load(sys.stdin) if d['type']=='tempo'])"
```

## Endpoint

```
GET https://<host>/grafana/api/datasources/proxy/uid/<ds-uid>/api/search
    ?q=<traceql>&start=<unix>&end=<unix>&limit=<n>
```

Related endpoints on the same proxy: `/api/traces/{traceID}` (fetch one
trace), `/api/search/tags`, `/api/search/tag/{tag}/values`.

## `validate_examples.py` — Run every documented example

Walks the per-operator directories, extracts each fenced ` ```traceql `
block, runs it against the cluster, and reports PASS / EMPTY / FAIL.

```bash
python3 validate_examples.py
python3 validate_examples.py --only aggregation
```

The examples match the traces emitted by the APM demo pods in
`agents/apm/demo/instrumentation/` (`demo-python-service`,
`demo-java-service`, `demo-go-service`) — deploy those first if the
cluster has no other trace traffic.

## Operator examples

| Category | Operators |
|---|---|
| `comparison/` | `=`, `!=`, `=~`, `!~`, ordering (`>`, `>=`, `<`, `<=`) |
| `logical/` | `&&`, `\|\|` |
| `intrinsic/` | `duration`, `name`, `status`, `kind`, `traceDuration`, `event:name` |
| `aggregation/` | `count`, `avg`, `min`, `max`, `sum` scalar filters |
| `transform/` | `select`, `by` |

**Not supported on Kloudfuse** (see the TraceQL docs overview): structural
operators (`>>`, `>`, `~`), TraceQL metrics functions, and the
`trace:`-scoped / `rootServiceName` intrinsic spellings.
