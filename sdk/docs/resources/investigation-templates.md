# `cz.investigation_templates`

Pre-configured investigation patterns. A template defines the
investigation logic; you supply **leads** (subjects to investigate)
when triggering it via [`cz.investigations.create_from_template(...)`](investigations.md).

Common templates (deployment-specific): employee separation reviews,
user last-day investigations, dormant account reviews, contractor
access expiration audits.

## Endpoints

| | Method |
|---|---|
| `cz.investigation_templates.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/investigations/templates` |
| `cz.investigation_templates.get(template_id, organization_id=…)` | `GET /organizations/{org}/investigations/templates/{id}` |

## Returns

`PaginatedIterator[InvestigationTemplate]` and `InvestigationTemplate`.
Fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | Pass to `cz.investigations.create_from_template(template_id=...)` |
| `name` | `str` | Slug, e.g. `"users-last-day"` |
| `title` | `str \| None` | Display name |
| `description` | `str \| None` | What the template investigates |
| `scenario` | `str \| None` | Category (e.g. `BUSINESS-EMAIL-COMPROMISE-(BEC)`, `ACCOUNT-ACCESS`) |
| `severity` | `str \| None` | Default severity (open enum) |
| `sensitivity` | `str \| None` | Default TLP-style sensitivity |
| `lead_types` | `list[str]` | Catalog type IDs the template accepts as leads (e.g. `["EMAIL_ADDRESS"]`) |
| `assignees` | `list[UserReference]` | Default assignees |
| `tags` | `list[str]` | Default tags |
| `sliding_date` | `str \| None` | Time-window scoping behavior |
| `created_by` / `updated_by` | `Attribution \| None` | |
| `created_time` / `updated_time` | `datetime \| None` | |

## Examples

Discover available templates:

```python
for tpl in cz.investigation_templates.list():
    print(tpl.name.ljust(30), tpl.lead_types, tpl.title)
```

Find templates that take an email address as a lead:

```python
for tpl in cz.investigation_templates.list():
    if "EMAIL_ADDRESS" in tpl.lead_types:
        print(tpl.name)
```

Look up a specific template:

```python
last_day = cz.investigation_templates.get("users-last-day")
print(last_day.description)
print("accepts:", last_day.lead_types)
```

Filter by scenario:

```python
bec = cz.investigation_templates.list(filter="scenario eq 'BUSINESS-EMAIL-COMPROMISE-(BEC)'")
```

## Use it for

- **Discovery in your SOAR**: enumerate templates at startup so the
  playbook UI can offer them as choices.
- **Compatibility checks**: confirm a template accepts the lead type
  you have before triggering it.
- **Documentation**: surface descriptions and default tags in your
  internal runbooks.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /investigations/templates` | responder, administrator |
| `GET /investigations/templates/{id}` | responder, administrator |

`investigator` role often **cannot** list templates — see
[troubleshooting](../troubleshooting.md). Trigger investigations
directly with the known template id instead, or use a key with a
broader role for discovery.

## Filtering

Filterable fields: `name`, `scenario`, `severity`, `sensitivity`.

## Notes

- Triggering a template uses
  [`cz.investigations.create_from_template`](investigations.md), not
  this resource.
- Template availability is deployment-specific. The blog example
  `users-last-day` exists in many but not all deployments — confirm
  by listing templates in your tenant.
