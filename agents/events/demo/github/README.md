# Events Demo — GitHub Webhook

A shell script that sends a synthetic **GitHub push event** payload directly to the Kloudfuse
ingestion endpoint, validating that the GitHub → Kloudfuse webhook pipeline is working end-to-end.

## How it works

`send-event.sh` constructs a JSON payload that mirrors a real GitHub `push` event and POSTs it to:

```
https://<kloudfuse-hostname>/ingester/github/events
```

The request includes the `X-GitHub-Event: push` header that Kloudfuse uses to classify the event
type. The ingested event is queryable in Kloudfuse as `source="github" x_github_event="push"`.

## Prerequisites

- `curl` and `openssl` available in your shell.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an ingestion API key.

## Run

```bash
export KFUSE_HOST="kloudfuse.example.com"
export KFUSE_API_KEY="<your-api-key>"   # omit if auth is not enabled

bash send-event.sh
```

Expected output:

```
Sending push event to https://kloudfuse.example.com/ingester/github/events
Commit SHA: a3f8c2...

HTTP status: 200
SUCCESS — event delivered.

Query in Kloudfuse:
  source="github" x_github_event="push"
```

## Verify events in Kloudfuse

GitHub events are stored in the **Events store**. Query via the `/events-query` GraphQL API:

```graphql
{
  events(
    durationSecs: 300,
    filter: { and: [{eq: {name: "@source", value: "github"}}] },
    timestamp: "<ISO-8601-timestamp>",
    limit: 10
  ) {
    id title text severity source eventType timestamp
  }
}
```

The event should appear within ~60 seconds with:
- `source: "github"`
- `eventType: "github.push"`
- `title`: `"demo-user push on demo-org/demo-repo"`
- `text`: full webhook payload as JSON (includes commit SHA, ref, pusher)

Filter to only the push event type:
```graphql
filter: { and: [{eq: {name: "eventType", value: "github.push"}}] }
```

## Setting up a real GitHub webhook

To receive live events from a real GitHub repository, configure a webhook in GitHub:

1. Go to your repository **Settings > Webhooks > Add webhook**.
2. Set **Payload URL** to `https://<kloudfuse-hostname>/ingester/github/events`.
3. Set **Content type** to `application/json`.
4. If auth is enabled, add header `Kf-Api-Key: <your-api-key>`.
5. Select **Send me everything** (or choose specific event types).
6. Click **Add webhook**.

See the [Kloudfuse GitHub integration docs](https://docs.kloudfuse.com/platform/latest/data-collection/github)
for full instructions and troubleshooting.
