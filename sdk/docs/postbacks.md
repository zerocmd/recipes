# Postbacks

Long-running operations (start-investigation, create-remediation)
support a **postback URL** — Command Zero sends the completion payload
to your URL via POST (or PUT) when the operation finishes. This is the
preferred alternative to polling.

## Configuring a postback

Pass a `postback` argument to any operation that supports it:

```python
cz.investigations.create_from_alert(
    alert_data={"sender": {"email": "x@y.com"}},
    alert_type="EmailMalware",
    postback={
        "url": "https://soar.internal/callbacks/cmdzero",
        "token": "shared-secret-please-rotate",   # sent back as Bearer header
        "method": "POST",                          # or "PUT"; default POST
    },
)
```

The `token` you set is sent back to your endpoint as
`Authorization: Bearer <token>` so you can verify the caller. **Treat
it as a secret** — rotate it on the same cadence as your other
inbound webhook secrets.

The `method` field defaults to `POST` and accepts `PUT` for systems
that want idempotent webhook delivery semantics.

## Payload shapes

The SDK ships pydantic models for both payload types:

### `InvestigationPostbackPayload`

Fields the SDK models (every required field plus the common optionals):

```python
from cmdzero import InvestigationPostbackPayload

payload = InvestigationPostbackPayload.model_validate(request_json)
payload.investigation_id     # UUID
payload.organization_id      # UUID
payload.status               # str: 'completed' or 'failed'
payload.severity             # str: 'critical'|'high'|'medium'|'low'|'informational' (case may vary)
payload.summary              # markdown string
payload.verdict              # list[str]
payload.observables          # list[Observable]
payload.console_url          # str
payload.error                # str (only set if status == 'failed')
payload.created_by           # Attribution
payload.created_time         # datetime
payload.updated_by           # Attribution
payload.updated_time         # datetime
payload.completed_time       # datetime | None
```

### `RemediationPostbackPayload`

```python
from cmdzero import RemediationPostbackPayload

payload = RemediationPostbackPayload.model_validate(request_json)
payload.remediation_id       # UUID
payload.organization_id      # UUID
payload.template_id          # str
payload.template_name        # str
payload.subject              # RemediationSubject {type, value}
payload.status               # str: pending|success|failed|not_found|unchanged|interrupted
payload.result               # arbitrary dict shaped per remediation template (may be None)
payload.error                # str | None
payload.console_url          # str
payload.created_by           # Attribution
payload.completed_time       # datetime | None
```

Models use `extra='allow'`, so additional fields the server adds in
future API versions deserialize without raising.

## Receiver template (Flask)

A complete reference receiver lives at the project root —
[`postback_receiver.py`](../../postback_receiver.py). The shape:

```python
from flask import Flask, abort, request, jsonify
from cmdzero import InvestigationPostbackPayload, RemediationPostbackPayload

EXPECTED_TOKEN = os.environ["CMDZERO_POSTBACK_TOKEN"]

app = Flask(__name__)

def _check_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        abort(401)
    if header.removeprefix("Bearer ") != EXPECTED_TOKEN:
        abort(401)

@app.post("/callback/investigations")
def on_investigation():
    _check_token()
    payload = InvestigationPostbackPayload.model_validate(request.get_json())
    log.info("investigation %s status=%s severity=%s",
             payload.investigation_id, payload.status, payload.severity)
    # do something with payload...
    return jsonify({"ok": True}), 200

@app.post("/callback/remediations")
def on_remediation():
    _check_token()
    payload = RemediationPostbackPayload.model_validate(request.get_json())
    log.info("remediation %s status=%s", payload.remediation_id, payload.status)
    return jsonify({"ok": True}), 200
```

Run it: `python postback_receiver.py --port 8080`. Pair with a tunnel
(ngrok, Cloudflare Tunnel, etc.) for local testing.

## Auto-remediation pattern

A common shape: when an investigation comes back malicious with high
confidence, kick off a remediation immediately. See
[examples/automated-remediation](examples/automated-remediation.md).

## Delivery semantics

Command Zero retries postback delivery on failure (5xx response,
connection error, timeout). To stay safe:

- **Make your handler idempotent** — process by
  `investigation_id` / `remediation_id` so a retried delivery doesn't
  double-act.
- **Acknowledge fast** — return 2xx within the receive timeout, even if
  downstream processing is slow. Defer heavy work to a queue.
- **Validate the bearer token on every call** — the token is your only
  authentication.
- **Don't trust the payload's claimed action** — re-fetch the
  investigation/remediation if you need authoritative state, in case
  the postback was triggered by a benign retry of an already-processed
  item.

## Polling alternative

If your environment can't accept inbound webhooks, poll the resource:

```python
import time

while True:
    inv = cz.investigations.get(investigation_id)
    if inv.status in ("completed", "failed"):
        break
    time.sleep(5)

handle_completion(inv)
```

Polling adds latency and consumes rate-limit budget — webhooks are
preferred when feasible.
