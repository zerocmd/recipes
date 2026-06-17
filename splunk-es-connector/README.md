# C0 ↔ Splunk ES Connector

A Python service that bridges Splunk Enterprise Security notables to Command Zero investigations. The connector polls Splunk for new notables, submits them to C0 for analysis, polls for verdicts, and writes results back onto the ES notable.

## How it works

Each tick of the main loop runs four steps:

1. **Poll Splunk** — searches `index=notable` since the last checkpoint, records new notables in a local SQLite store.
2. **Submit to C0** — for each unsubmitted notable, POSTs a C0 investigation. Only notables whose alert type has a schema defined in `schemas.py` are submitted; notables with no mapped schema are recorded as `NO_SCHEMA` and never sent (see [Alert schemas](#alert-schemas) — this is an intentional filter). On the first submission of a given alert type, the connector includes an `alertSchema` so C0 knows which fields contain observables; C0 caches this schema for subsequent submissions.
3. **Poll C0** — fetches the current status of all open investigations. When an investigation carries a non-empty verdict at any post-automation status (`pending-review`, `in-progress`, `on-hold`, or `completed`), the record is marked ready. Investigations that never produce a verdict within one day are given up on and marked failed.
4. **Write back** — optionally posts the verdict as a comment on the ES notable via `notable_update` (requires ES; can be disabled with `SPLUNK_ES_WRITEBACK=false`), then sends a structured enrichment event to a Splunk HEC index (`c0_enrichment`) for dashboarding. When the comment step is enabled, it runs first and its success is persisted before the HEC step, so a HEC failure that triggers a retry never re-posts the comment.

## Prerequisites

- Python 3.11+ (3.12 or 3.13 recommended; 3.11 is the minimum)
- [uv](https://docs.astral.sh/uv/) package manager
- Splunk Enterprise (ES is only required for the `notable_update` comment writeback; set `SPLUNK_ES_WRITEBACK=false` to skip that step if you don't have ES)
- A Command Zero organization ID and bearer token

## Setup

### 1. Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Install connector dependencies

```bash
uv sync
```

### 3. Create a Splunk service account token

The connector authenticates to the Splunk REST API using a long-lived token
(not a username/password). To generate one:

1. In the Splunk UI go to **Settings → Tokens** (under the Users and Authentication section).  
   If you don't see this menu, enable token authentication first:  
   **Settings → Token Authentication → Enable**.
2. Click **New Token**.
3. Set a meaningful name (e.g. `c0-connector`) and an appropriate expiry.
4. The generated token is the value for `SPLUNK_SVC_TOKEN`.

The service account running the connector needs:
- The `user` role or higher (to submit and poll search jobs on `index=notable`)
- The `can_delete` capability is **not** required

### 4. Enable HEC and create an HEC token (optional)

The HEC path writes structured enrichment events to a `c0_enrichment` index.
It is optional — leave `SPLUNK_HEC_URL` blank in `.env` to skip this step.

To enable it:

1. **Enable HEC globally:** Settings → Data inputs → HTTP Event Collector → Global Settings → set "All tokens" to **Enabled**.
2. **Create a token:** New Token → name it (e.g. `c0-enrichment`) → set the default index to `c0_enrichment`.
3. The token value is the value for `SPLUNK_HEC_TOKEN`.
4. **Create the `c0_enrichment` index** (Splunk will reject HEC events to a non-existent index):

   ```bash
   curl -sk -u admin:'<password>' https://<splunk-host>:8089/services/data/indexes \
     -d name=c0_enrichment
   ```

   Or: Settings → Indexes → New Index → name `c0_enrichment`.

### 5. Configure credentials

```bash
cp .env.example .env
# Edit .env — at minimum set C0_ORG_ID, C0_BEARER_TOKEN, SPLUNK_REST_URL, SPLUNK_SVC_TOKEN
```

## Splunk Cloud

The connector runs against Splunk Cloud unchanged, but the endpoints and the index-creation step differ from on-prem:

- **REST URL.** Use the stack's management endpoint, `https://<stack>.splunkcloud.com:8089`. Port 8089 is not open by default on Cloud — add the connector's egress IP to the **Settings → Server Settings → IP Allow List** (the *Splunk Cloud Management* / `s2s` and REST category) before the preflight check will pass.
- **ES on a separate search head.** On Cloud, Enterprise Security usually runs on its own search head with a different hostname than the one serving `index=notable`. Point `SPLUNK_ES_REST_URL` at the ES search head; leave it blank only if both share one host.
- **HEC host.** Cloud HEC is a distinct hostname on port 443, not `:8088`: `https://http-inputs-<stack>.splunkcloud.com:443/services/collector/event`. Set `SPLUNK_HEC_URL` accordingly.
- **Index creation.** The `curl … /services/data/indexes` call in step 4 is blocked on Cloud — REST index management is not permitted. Create `c0_enrichment` through the UI (**Settings → Indexes → New Index**) or the [Admin Config Service (ACS) API](https://docs.splunk.com/Documentation/SplunkCloud/latest/Config/ManageIndexes) instead.

Token creation (step 3), HEC enablement, and all `.env` settings are otherwise identical to on-prem.

## Running

```bash
uv run connector
```

The connector performs a preflight check on startup, verifying connectivity and authentication for both Splunk and C0 before entering the main loop. If any required value is missing or authentication fails, it exits with a clear error message.

Stop with `Ctrl-C` or `SIGTERM` — the process shuts down cleanly after the current tick completes.

## Configuration

All settings are read from environment variables or `.env`. Defaults are shown.

| Variable | Required | Default | Description |
|---|---|---|---|
| `C0_ORG_ID` | yes | — | Your C0 organization UUID |
| `C0_BEARER_TOKEN` | yes | — | C0 API bearer token |
| `C0_API_BASE_URL` | no | `https://api.cmdzero.io/public/v1` | C0 API base URL |
| `SPLUNK_REST_URL` | yes | — | REST endpoint of the search head that owns `index=notable` (e.g. `https://localhost:8089`) |
| `SPLUNK_ES_REST_URL` | no | _(falls back to `SPLUNK_REST_URL`)_ | REST endpoint of the ES search head, used for the `notable_update` writeback. Set only when ES runs on a separate search head (common on Splunk Cloud). Ignored when `SPLUNK_ES_WRITEBACK=false` |
| `SPLUNK_SVC_TOKEN` | yes | — | Splunk service account token |
| `SPLUNK_ES_WRITEBACK` | no | `true` | Post verdict as a comment on the ES notable via `notable_update`. Set `false` if Splunk ES is not installed — the HEC enrichment step still runs |
| `SPLUNK_HEC_URL` | no | _(empty)_ | HEC endpoint; leave blank to disable enrichment writeback |
| `SPLUNK_HEC_TOKEN` | no | _(empty)_ | HEC token |
| `SPLUNK_VERIFY_TLS` | no | `true` | Verify Splunk's TLS certificate (REST + HEC). Set `false` only for self-signed certs — see [TLS verification](#tls-verification) |
| `NOTABLE_INDEX` | no | `notable` | Splunk index to poll |
| `ENRICHMENT_INDEX` | no | `c0_enrichment` | Splunk HEC index for enrichment events |
| `SPLUNK_POLL_INTERVAL` | no | `300` | Seconds between Splunk polls |
| `POLL_WINDOW_OVERLAP` | no | `600` | Overlap seconds subtracted from the checkpoint to handle indexing lag; set to at least 2× `SPLUNK_POLL_INTERVAL` |
| `C0_POLL_INTERVAL` | no | `300` | Base seconds between C0 verdict polls (exponential backoff applied per record) |
| `C0_POLL_MAX_BACKOFF` | no | `1800` | Per-record backoff ceiling (seconds) |
| `C0_SUBMIT_DELAY` | no | `2.0` | Pause (seconds) between consecutive C0 submissions to avoid burst rate-limiting |
| `ALERT_TYPE_PREFIX` | no | `SplunkES` | Prefix applied to alert types sent to C0 (e.g. `SplunkES:Access - Brute Force...`) |
| `AUTO_DISPOSITION` | no | `false` | **Not yet implemented.** Reserved flag intended to automatically set the ES notable disposition from the C0 verdict. Requires a live Splunk ES instance to build and test against — see the implementation note in `config.py`. Setting it has no effect today. |
| `DB_PATH` | no | `connector.db` | Path to the SQLite state database |

## Alert schemas

`schemas.py` is both the **allow-list** and the **schema registry**. Only correlation searches present in `SCHEMAS` are forwarded to Command Zero — all others are dropped at discovery time and never submitted.

Each entry maps an alert type to one of two values:

**Explicit schema** — a list of TypeAnnotation dicts that tell C0 which fields contain observables. The connector sends this on the first submission of the alert type; C0 caches it for subsequent submissions.

```python
SCHEMAS["SplunkES:My New Rule - Rule"] = [
    {"path": "rule_title",       "type": "ALERT_TITLE"},
    {"path": "rule_description", "type": "ALERT_DESCRIPTION"},
    {"path": "event_id",         "type": "ALERT_ID"},
    {"path": "_time",            "type": "ALERT_TIME"},
    {"path": "src_ip",           "type": "IP_ADDRESS"},
    {"path": "user",             "type": "USER"},
]
```

**Auto-schema (`None`)** — the alert type is allowed but no schema is provided. C0 will infer observables from the alert data automatically using auto-schema.

```python
SCHEMAS["SplunkES:My New Rule - Rule"] = None
```

**Type values must be valid C0 lead types** — invalid types cause a `400 Unknown type` error at submission time. Common types:

| Type | Meaning |
|---|---|
| `ALERT_TITLE` | Correlation search name |
| `ALERT_DESCRIPTION` | Rule description |
| `ALERT_ID` | Notable event ID |
| `ALERT_TIME` | Event timestamp |
| `IP_ADDRESS` | Source or destination IP |
| `HOST_NAME` | Hostname |
| `USER` | Username or account |
| `URL` | Web URL |
| `DOMAIN_NAME` | Domain |
| `FILE_NAME` | File path or name |
| `SHA_256` | File hash |

The authoritative type list lives in `schemas.py`.

### The allow-list filter

Alert types not present in `SCHEMAS` are stored locally as `NO_SCHEMA` (a terminal state) and never submitted to C0. This is intentional — the connector only forwards correlation searches you have explicitly opted in, keeping the integration deliberate during rollout.

To start forwarding a new correlation search, add it to `schemas.py` with either an explicit schema or `None`. Until then, its notables are tracked locally as `NO_SCHEMA` and ignored. A notable stuck in `NO_SCHEMA` after you've added an entry simply means it was discovered before the entry existed; re-poll picks up only *new* notables, so the change applies going forward.

## Project structure

```
connector.py   — main loop and entrypoint
c0.py          — C0 API client (submit, poll, 429 retry)
splunk.py      — Splunk client (poll notables, write_verdict, HEC)
schemas.py     — alertSchema definitions per correlation search type
store.py       — SQLite-backed notable lifecycle store
config.py      — pydantic-settings Config model
```

## State machine

Each notable moves through the following states in the SQLite store:

```
DISCOVERED → INVESTIGATING → VERDICT_READY → COMMENT_DONE → WRITTEN_BACK
                ↓ (if C0 merges with existing)
              MERGED → VERDICT_READY → COMMENT_DONE → WRITTEN_BACK
                                  ↓ (on repeated failure / no verdict after 1 day)
                                FAILED

NO_SCHEMA  (terminal — recorded at discovery for alert types with no mapped schema;
            never submitted to C0; see "Alert schemas")
```

`NO_SCHEMA` is a terminal state set at discovery time when the notable's alert type
has no entry in `schemas.py`. It is the filtering mechanism described under
[Alert schemas](#alert-schemas): the record is persisted so the notable isn't
rediscovered every poll, but it is never submitted.

`VERDICT_READY` means C0 has finished its automated analysis and a verdict is ready to write back to Splunk. This is triggered by a non-empty verdict at any post-automation status (`pending-review`, `in-progress`, `on-hold`, `completed`) — not just `pending-review` — so a verdict isn't lost if an analyst has already advanced the case. The actual C0 status is passed through to the `c0_enrichment` HEC index as `c0_status`.

`COMMENT_DONE` is an intermediate state that separates the two writeback steps. When `SPLUNK_ES_WRITEBACK=true` (the default), it is recorded the moment the `notable_update` comment POST succeeds, so a subsequent HEC failure retries only the HEC step and never re-posts the comment. When `SPLUNK_ES_WRITEBACK=false`, the record advances directly to `COMMENT_DONE` without calling `notable_update`, then the HEC step runs immediately.

The connector retries failed submissions up to 5 times and failed writebacks up to 5 times before marking a record `FAILED`. An investigation that never returns a verdict is marked `FAILED` after one day of polling.

## Rate limiting

The C0 client retries `429 Too Many Requests` responses up to 3 times, honoring the `Retry-After` header (defaulting to 60 seconds if the header is absent). The `C0_SUBMIT_DELAY` setting (default 2 seconds) adds a pause between consecutive POSTs to avoid hitting burst limits in the first place.

## TLS verification

`SPLUNK_VERIFY_TLS` defaults to `true` (REST + HEC). Set it `false` only if your
Splunk instance presents a self-signed certificate.

## Known limitations

- **`notable_update` requires Splunk Enterprise Security.** The comment writeback returns a 404 on Splunk Enterprise or Trial (no ES module). Set `SPLUNK_ES_WRITEBACK=false` to skip this step entirely; the HEC enrichment path is unaffected.
- **Alert schemas must be defined per correlation search.** `schemas.py` ships with four example types; extend it for your environment's correlation searches.
