# Alert ingestion (SIEM / SOAR)

Use case: your SIEM or SOAR receives an alert and your playbook hands
it to Command Zero to drive an automated investigation. When the
investigation completes Command Zero calls back to your playbook, which
populates the incident ticket with the verdict, summary, and
observables before an analyst ever opens it.

## Choose your alert form

The API accepts three input shapes on `POST /investigations`. Pick the
one that fits how your alert source maps onto Command Zero's catalog.

### Form 1: Built-in `alertType`

If Command Zero already understands your alert source (CrowdStrike,
Recorded Future, etc.), pass `alert_type` and `alert_data` and the
schema is resolved automatically.

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    inv = cz.investigations.create_from_alert(
        alert_type="EmailMalware",      # built-in known alert type
        alert_data={
            "sender": {"email": "badactor@example.com"},
            "file": {"sha256": "275a021bbfb6489e54d471899f7db9d1663fc695ec2fe2a2c4538aabf651fd0f"},
            "seen": "2026-01-13T15:00:00Z",
        },
        title="Malicious attachment detected",
        tags=["siem-integration", "email-malware"],
    )

print(inv.id, inv.action)        # action: 'created' or 'merged'
```

### Form 2: Custom alert with inline schema

For sources without a built-in schema, declare the type annotations
inline:

```python
inv = cz.investigations.create_from_alert(
    alert_type="AcmeSiemEmailAlert",      # arbitrary identifier
    alert_data={
        "alert_title": "Suspicious sender",
        "sender": {"email": "x@y.com"},
        "file": {"sha256": "275a021..."},
        "seen": "2026-04-27T15:00:00Z",
    },
    alert_schema=[
        {"path": "alert_title", "type": "ALERT_TITLE"},
        {"path": "sender.email", "type": "EMAIL_ADDRESS"},
        {"path": "file.sha256",  "type": "SHA_256"},
        {"path": "seen",         "type": "ALERT_TIME"},
    ],
)
```

### Form 3: catalog-type schema string

If your alert is essentially a single observable, pass the catalog
type ID as `alert_schema` and omit `alert_type`:

```python
inv = cz.investigations.create_from_alert(
    alert_data={"address": "suspicious@example.com"},
    alert_schema="EMAIL_ADDRESS",
)
```

## Add a postback so the playbook hears back

Polling for completion works but adds latency and burns rate-limit
budget. The preferred pattern is a postback URL — Command Zero POSTs
the completed investigation to your endpoint:

```python
inv = cz.investigations.create_from_alert(
    alert_type="EmailMalware",
    alert_data={...},
    title="Malicious attachment detected",
    postback={
        "url": "https://your-soar.internal/callback/cmdzero/investigations",
        "token": "shared-webhook-secret",     # sent back as Bearer
    },
)
```

The receiver then handles the completion event. See
[postbacks](../postbacks.md) for a full Flask receiver pattern.

## Alert merging

The response carries `action='created'` when a new investigation
started, or `action='merged'` when this alert was rolled into an
in-flight investigation already examining the same activity. Don't
open a duplicate ticket on your side — reference `inv.id`:

```python
if inv.action == "merged":
    log.info("alert merged into existing investigation %s", inv.id)
    siem.update_ticket(siem_alert_id, cmdzero_id=str(inv.id))
else:
    siem.create_ticket(cmdzero_id=str(inv.id), title=inv.title)
```

## Worked end-to-end pattern

```python
from cmdzero import CommandZero, RateLimitError, CommandZeroError

ALERT_FROM_SIEM = {       # whatever your playbook hands you
    "alert_id": "siem-12345",
    "title": "Malicious attachment detected",
    "sender": {"email": "badactor@example.com"},
    "file": {"sha256": "275a021..."},
    "seen": "2026-04-27T14:30:00Z",
}

def submit(alert: dict) -> str:
    with CommandZero() as cz:
        try:
            resp = cz.investigations.create_from_alert(
                alert_type="EmailMalware",
                alert_data={
                    "sender": alert["sender"],
                    "file": alert["file"],
                    "seen": alert["seen"],
                },
                title=alert["title"],
                tags=["siem-integration", f"siem-id={alert['alert_id']}"],
                postback={
                    "url": "https://soar.internal/cb/investigations",
                    "token": os.environ["POSTBACK_SECRET"],
                },
            )
            return str(resp.id)
        except RateLimitError as e:
            # the SDK already retried; you've exhausted the budget
            log.warning("cmdzero throttled, deferring trace=%s", e.trace_id)
            raise
        except CommandZeroError as e:
            log.error("cmdzero submit failed status=%s trace=%s", e.status, e.trace_id)
            raise
```

## Reference scripts

- [`alert_investigation.py`](../../../alert_investigation.py) — CLI script
  that submits a demo alert.
- [`postback_receiver.py`](../../../postback_receiver.py) — Flask
  receiver that validates the bearer token and persists payloads.

## Permissions

`POST /investigations` requires the `investigator` role or above. See
[authentication](../authentication.md).
