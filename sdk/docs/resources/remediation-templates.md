# `cz.remediation_templates`

Catalog of remediation actions configured for the org. Each template
defines what action is taken (disable user, isolate host, revoke
session, etc.), what subject type it applies to, and — when reversible
— its `undoTemplateId`.

## Endpoints

| | Method |
|---|---|
| `cz.remediation_templates.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/remediations/templates` |
| `cz.remediation_templates.get(template_id, organization_id=…)` | `GET /organizations/{org}/remediations/templates/{id}` |
| `cz.remediation_templates.for_subject_type(subject_type, organization_id=…)` | shortcut for `list(filter="subjectType eq '<type>'")` |

## Returns

`PaginatedIterator[RemediationTemplate]` and `RemediationTemplate`.
Fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Pass to `cz.remediations.create(template_id=...)` |
| `name` | `str` | Internal slug |
| `display_name` | `str \| None` | Human-readable name |
| `description` | `str \| None` | What the action does |
| `subject_type` | `str \| None` | Catalog type ID this template targets |
| `undo_template_id` | `str` | Template id of the inverse action; empty string if not reversible |
| `created_by` / `updated_by` | `Attribution \| None` | |
| `created_time` / `updated_time` | `datetime \| None` | |

## Examples

List every remediation template available:

```python
for tpl in cz.remediation_templates.list():
    undo = "yes" if tpl.undo_template_id else "no"
    print(f"{tpl.id:<24} subject={tpl.subject_type:<35} undo={undo}  {tpl.display_name}")
```

Find templates that target Entra users:

```python
for tpl in cz.remediation_templates.for_subject_type("MICROSOFT_ENTRA_USER_PRINCIPAL_NAME"):
    print(tpl.id, tpl.display_name)
```

Look up a template's undo action:

```python
disable = cz.remediation_templates.get("r-disable-entra-user")
if disable.undo_template_id:
    enable = cz.remediation_templates.get(disable.undo_template_id)
    print("undo via:", enable.display_name)
```

## Use it for

- **Discovery in your SOAR**: cache the template list at startup so
  the playbook can pick the right action by name without hardcoding
  IDs.
- **Compatibility checks**: confirm `subject_type` matches the
  observable type from your investigation before issuing a
  remediation.
- **Reversibility**: read `undo_template_id` to decide whether your
  workflow can offer an undo button.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /remediations/templates` | responder, administrator |
| `GET /remediations/templates/{id}` | responder, administrator |

`investigator` typically cannot see remediation templates.

## Filtering

Filterable fields: `subjectType`, `name`, `displayName`.

```python
cz.remediation_templates.list(filter="contains(displayName, 'Disable')")
```

## Notes

- Available templates depend on the integrations active in your
  Command Zero tenant. A template that exists in one tenant may not
  in another.
- `subject_type` values are catalog type IDs — confirm with
  [`cz.catalog`](catalog.md) when your observable type is uncertain.
- Use [`cz.remediations.create`](remediations.md) to actually execute
  the action.
