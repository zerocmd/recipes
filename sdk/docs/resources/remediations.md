# `cz.remediations`

Execute remediation actions against subjects (users, hosts, sessions,
etc.) and track their outcomes. The blast-radius end of the API —
treat with care.

## Endpoints

| | Method |
|---|---|
| `cz.remediations.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/remediations` |
| `cz.remediations.get(remediation_id, organization_id=…)` | `GET /organizations/{org}/remediations/{id}` |
| `cz.remediations.create(template_id=, subject=, justification=…, postback=…, organization_id=…)` | `POST /organizations/{org}/remediations` |

## Returns

`Remediation`. Fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `organization_id` | `UUID` | |
| `template_id` | `str` | Which template was executed |
| `template_name` | `str \| None` | Display name of the template |
| `subject` | `RemediationSubject` | `{type: str, value: Any}` |
| `status` | `str` | open enum: `pending`, `success`, `failed`, `not_found`, `unchanged`, `interrupted` |
| `result` | `Any \| None` | Template-specific structured result. `None` while pending or on failure. |
| `error` | `str` | Empty unless `status='failed'` |
| `justification` | `str` | Whatever you supplied at create time, recorded for audit |
| `console_url` | `str \| None` | Direct link in the Command Zero UI |
| `created_by` / `updated_by` | `Attribution` | |
| `created_time` / `updated_time` | `datetime` | |
| `completed_time` | `datetime \| None` | Set when status is terminal |

## Status meanings

| Status | Meaning |
|---|---|
| `pending` | Queued or in flight |
| `success` | Completed successfully |
| `failed` | Action failed; check `error` |
| `not_found` | The subject didn't exist (already deleted, wrong identifier) |
| `unchanged` | Subject already in the desired state (e.g. user already disabled) |
| `interrupted` | Cancelled before completion |

This is an open enum — handle unknown values gracefully.

## Examples

Execute a remediation:

```python
rem = cz.remediations.create(
    template_id="r-disable-entra-user",
    subject={"type": "MICROSOFT_ENTRA_USER_PRINCIPAL_NAME",
             "value": "compromised.account@company.com"},
    justification="Automated containment: credential compromise confirmed, confidence high",
    postback={"url": "https://soar/cb/remediations", "token": "shh"},
)
print(rem.id, rem.status)        # often 'pending' on first response
```

Poll for completion (or use a postback):

```python
import time

while True:
    rem = cz.remediations.get(rem.id)
    if rem.status != "pending":
        break
    time.sleep(2)

print("final:", rem.status, "error:", rem.error)
```

Undo a remediation by executing its inverse template:

```python
# Look up the template + its undo
tpl = cz.remediation_templates.get(rem.template_id)
if not tpl.undo_template_id:
    raise RuntimeError("template is not reversible")

undo = cz.remediations.create(
    template_id=tpl.undo_template_id,
    subject=rem.subject,                 # same subject, inverse action
    justification=f"Reverting remediation {rem.id}: analyst review",
)
```

Audit trail for a specific subject:

```python
history = cz.remediations.list(
    filter="subject/type eq 'MICROSOFT_ENTRA_USER_PRINCIPAL_NAME'",
)
for r in history:
    if r.subject.value == target_email:
        print(r.created_time, r.template_name, r.status, r.justification)
```

## Use it for

- **Automated containment** after an investigation reaches a verdict.
  See [examples/automated-remediation](../examples/automated-remediation.md).
- **Reversal** of incorrect containment via `undo_template_id`.
- **Audit reporting**: query past remediations for compliance reviews.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /remediations` | responder, administrator |
| `QUERY /remediations` | responder, administrator |
| `GET /remediations/{id}` | responder, administrator |
| `POST /remediations` | responder, administrator |

## Filtering

Filterable: `status`, `templateId`, `subject/type`.

## Justification field

`justification` is stored permanently and surfaces in audit reports.
Make it specific:

✅ `"Auto-contained after investigation 8e2…7f confirmed BEC compromise"`
❌ `"automation"`

This is the trail your incident response team, auditors, and counsel
will read when asking "why was this account disabled?"

## Notes

- The `subject.type` you pass must match the template's `subject_type`.
  See [remediation-templates](remediation-templates.md).
- `MICROSOFT_ENTRA_USER` is **not** a real subject type. Use
  `MICROSOFT_ENTRA_USER_PRINCIPAL_NAME`.
- The `result` field shape depends on the template — for example, a
  disable-user template might return `{"disabledAt": "2026-04-27T…"}`,
  while a host-isolation template might return network-state details.
  Inspect `result` cautiously and don't rely on a fixed shape across
  templates.
- Combine remediation with a follow-up `cz.investigations.update(...)`
  to mark the investigation completed and tag the outcome.
