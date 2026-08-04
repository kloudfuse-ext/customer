# Logs Demo — Heroku Log Drain

Simulates the HTTPS POST that Heroku Logplex makes to a registered drain.
Sends a batch of realistic syslog-format log lines to Kloudfuse and verifies they arrive.

## How it works

- Heroku Logplex delivers logs over HTTPS as newline-delimited syslog frames (RFC 5424).
- Each frame is prefixed with its byte length: `<len> <syslog-message>`.
- Kloudfuse receives these at `/ingester/heroku/logs` and parses the syslog fields into labels.
- The drain token (`Logplex-Drain-Token` header) is stored as the `drain_token` label.

## Syslog frame format

```
<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME PROC-ID MSGID - MESSAGE
```

| Syslog field | Heroku meaning | Kloudfuse label |
|---|---|---|
| `HOSTNAME` | Heroku app name | `host_name` |
| `APP-NAME` | `app` (dyno) or `heroku` (platform) | `app_name` |
| `PROC-ID` | Dyno identifier (`web.1`, `router`) | `proc_id` |
| `Logplex-Drain-Token` header | Drain token assigned by Heroku | `drain_token` |

## Prerequisites

- `curl` and `python3` installed.
- The external hostname of your Kloudfuse cluster.
- If ingestion authentication is enabled, an API key.

## Run the demo

```bash
chmod +x send-drain.sh

# No auth:
./send-drain.sh kloudfuse.example.com

# With auth:
./send-drain.sh kloudfuse.example.com glsa_abc123...
```

The script sends 5 log frames (3 dyno logs, 1 router log, 1 platform state change),
waits 10 s, then queries Kloudfuse to confirm they arrived.

## Verify logs in Kloudfuse

Filter all logs from this demo:

```
{source="heroku"} |= "heroku-demo"
```

Filter only dyno (app) logs:

```
{source="heroku", log_type="app"}
```

Filter only platform/router logs:

```
{source="heroku", log_type="system"}
```

Filter by drain token:

```
{source="heroku", drain_token="d.abc12345-..."}
```
