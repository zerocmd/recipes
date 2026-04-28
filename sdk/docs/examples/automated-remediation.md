# Automated remediation

Use case: when an investigation reaches a confident-malicious verdict,
your integration executes containment automatically — disable the
account, isolate the host, revoke the session — and closes the
investigation with an audit-friendly justification. Reversible
actions can be undone if the analyst review later finds the
containment was wrong.

This is the highest-blast-radius use case in the API. Build the
threshold checks carefully and make every action audit-traceable.

## End-to-end shape

```text
SIEM alert
    ↓
cz.investigations.create_from_alert(..., postback={...})
    ↓                                                ┐
[Command Zero investigates]                          │ async
    ↓                                                │
your /callback/investigations receives postback     ┘
    ↓
your code:
    inspect verdict + confidence_level
    ↓ (if threshold met)
    cz.remediation_templates.for_subject_type(...)
    ↓
    cz.remediations.create(template_id, subject, justification)
    ↓
    cz.investigations.update(status="completed", tags=[...])
```

## Threshold gating

Don't auto-remediate on every malicious verdict. The minimum gate
should be: high confidence **and** a known-malicious verdict tag.

```python
CONFIDENCE_RANK = {"low": 1, "moderate": 2, "high": 3}
MALICIOUS = {"malicious", "true-positive", "confirmed-threat"}

def should_auto_remediate(payload) -> tuple[bool, str]:
    confidence = (payload.confidence_level or "").lower()
    if CONFIDENCE_RANK.get(confidence, 0) < CONFIDENCE_RANK["high"]:
        return False, f"confidence={confidence!r} below threshold"
    verdicts = {v.lower() for v in (payload.verdict or [])}
    if not (verdicts & MALICIOUS):
        return False, f"verdicts={sorted(verdicts)} not malicious"
    return True, "ok"
```

Tighten this for higher-risk actions. For example, require an explicit
allowlist of catalog types you'll auto-disable, and never auto-act on
VIP accounts even with high confidence.

## Pick the remediation template

```python
def find_template(cz, subject_type: str, name_hint: str | None = None):
    for tpl in cz.remediation_templates.for_subject_type(subject_type):
        if name_hint and name_hint not in (tpl.name, tpl.display_name or ""):
            continue
        return tpl
    return None
```

If your playbook is long-lived, cache the template lookup to avoid a
listing call per remediation.

## Execute

```python
def remediate(cz, subject: dict, template_id: str, investigation_id: str):
    rem = cz.remediations.create(
        template_id=template_id,
        subject=subject,
        justification=(
            f"Auto-contained after investigation {investigation_id}: "
            f"verdict=malicious, confidence=high"
        ),
        postback={
            "url": "https://soar/cb/remediations",
            "token": os.environ["WEBHOOK_SECRET"],
        },
    )
    return rem
```

The justification is stored permanently and surfaces in audit
reports. Make it specific — auditors will read it.

## Close out the investigation

After the remediation kicks off, mark the investigation `completed`
with outcome tags so it shows up in dashboards as auto-handled:

```python
cz.investigations.update(
    investigation_id,
    status="completed",
    tags=["auto-contained", "remediated", "credential-compromise"],
)
```

Tags fully replace the existing list. If you want to preserve prior
tags, fetch first:

```python
inv = cz.investigations.get(investigation_id)
preserved = list({*inv.tags, "auto-contained", "remediated"})
cz.investigations.update(investigation_id, status="completed", tags=preserved)
```

## Worked end-to-end pattern

```python
import os, logging
from cmdzero import CommandZero, ForbiddenError

log = logging.getLogger(__name__)

CONFIDENCE_RANK = {"low": 1, "moderate": 2, "high": 3}
MALICIOUS = {"malicious", "true-positive", "confirmed-threat"}

def handle_postback(payload):
    """Called from your /callback/investigations Flask handler."""
    confidence = (payload.confidence_level or "").lower()
    if CONFIDENCE_RANK.get(confidence, 0) < CONFIDENCE_RANK["high"]:
        log.info("skip auto-remediation: confidence=%s", confidence)
        return
    verdicts = {v.lower() for v in (payload.verdict or [])}
    if not (verdicts & MALICIOUS):
        log.info("skip auto-remediation: verdicts=%s", sorted(verdicts))
        return

    subject = pick_subject(payload.observables)
    if not subject:
        log.info("skip auto-remediation: no actionable subject")
        return

    with CommandZero() as cz:
        tpl = next(cz.remediation_templates.for_subject_type(subject["type"]), None)
        if not tpl:
            log.warning("no template for subject_type=%s", subject["type"])
            return

        try:
            rem = cz.remediations.create(
                template_id=tpl.id,
                subject=subject,
                justification=(
                    f"Auto-contained after investigation {payload.investigation_id}: "
                    f"verdict={sorted(verdicts)}, confidence=high"
                ),
            )
        except ForbiddenError as e:
            log.error("role lacks remediation rights trace=%s", e.trace_id)
            return

        cz.investigations.update(
            payload.investigation_id,
            status="completed",
            tags=["auto-contained", "remediated"],
        )

    log.info("remediation %s issued for %s", rem.id, payload.investigation_id)


def pick_subject(observables):
    """Pick the first observable that's a usable remediation subject."""
    for obs in observables or []:
        if obs.type == "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME":
            return {"type": obs.type, "value": obs.value}
    return None
```

## Reversal (undo)

Every reversible template carries an `undo_template_id`. Execute the
inverse to roll back:

```python
def undo(cz, remediation_id: str, reason: str):
    rem = cz.remediations.get(remediation_id)
    tpl = cz.remediation_templates.get(rem.template_id)
    if not tpl.undo_template_id:
        raise RuntimeError(f"template {tpl.name} is not reversible")

    return cz.remediations.create(
        template_id=tpl.undo_template_id,
        subject=rem.subject,
        justification=f"Reverting remediation {remediation_id}: {reason}",
    )
```

## Reference scripts

- [`automated_remediation.py`](../../../automated_remediation.py) — CLI
  with `templates` (list), `contain` (execute with threshold gate),
  `undo` (reverse). The default threshold is `--min-confidence high`
  with the malicious-verdict requirement.
- [`postback_receiver.py`](../../../postback_receiver.py) — Flask
  receiver with an optional `--auto-remediate` mode that wires the
  postback handler shown above.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /remediations/templates` | responder, administrator |
| `POST /remediations` | responder, administrator |
| `PATCH /investigations/{id}` | investigator or above |

Auto-remediation requires at least `responder`. For least-privilege,
use a dedicated key per action class.

## Production guardrails

Before turning auto-remediation on in production:

1. **Confirm template behavior in staging.** Run each template against
   a known test subject and inspect the resulting `result` and
   `error` fields.
2. **Maintain an exception list** of subjects that must never be
   auto-acted on (executive accounts, service accounts critical to
   your stack).
3. **Alert on every remediation**, not just failures. Send a Slack
   message with the investigation link and the justification text so
   humans see what the automation did.
4. **Keep the postback receiver idempotent.** If Command Zero retries
   a postback after your handler crashed mid-flight, you don't want
   to issue a second remediation.
5. **Have an undo runbook.** When you need to reverse an automated
   action at 2am, the steps should already be written down.
