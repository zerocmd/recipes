# Template-based investigations

Use case: an upstream system fires a triggering event (HR processes a
separation, IAM flags a dormant account, your contractor management
system marks an access-expiry date), and your integration starts a
pre-configured investigation against the affected identity.

Templates encode the investigation logic; you supply leads and an
optional time window.

## Discover templates

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    for tpl in cz.investigation_templates.list():
        print(tpl.name.ljust(30), tpl.lead_types, tpl.title)
```

Templates accept a fixed list of lead types — the `lead_types` field
on each template tells you what catalog type IDs are valid as leads.
Filter to templates that take an email address:

```python
email_templates = [
    tpl for tpl in cz.investigation_templates.list()
    if "EMAIL_ADDRESS" in tpl.lead_types
]
```

## Trigger a template

```python
from datetime import datetime, timezone

inv = cz.investigations.create_from_template(
    template_id="users-last-day",
    leads=[{"type": "EMAIL_ADDRESS", "value": "departing@company.com"}],
    title="Last day review — J. Smith",
    start_time=datetime(2026, 4, 1, tzinfo=timezone.utc),
    end_time=datetime(2026, 4, 27, tzinfo=timezone.utc),
    tags=["hr-separation"],
)
print(inv.id, inv.action)
```

`start_time` and `end_time` scope the investigation window. They
default to a 7-day window ending at the current time — useful for
"recent activity" template patterns. Override when you want a
specific period (e.g. 30 days before the departure date).

## Common patterns

### HR separation processed

```python
def on_separation(employee_email: str, last_day: datetime):
    with CommandZero() as cz:
        inv = cz.investigations.create_from_template(
            template_id="users-last-day",
            leads=[{"type": "EMAIL_ADDRESS", "value": employee_email}],
            title=f"Separation review — {employee_email}",
            start_time=last_day - timedelta(days=30),
            end_time=last_day,
            tags=["hr-separation"],
            postback={"url": "https://soar/cb", "token": os.environ["WEBHOOK_SECRET"]},
        )
    log.info("started separation investigation %s", inv.id)
```

### Contractor access expiry

```python
def on_contractor_expiry(account: str):
    with CommandZero() as cz:
        cz.investigations.create_from_template(
            template_id="dormant-account-review",
            leads=[{"type": "EMAIL_ADDRESS", "value": account}],
            title=f"Contractor expiry — {account}",
            tags=["contractor", "expiry"],
        )
```

### Multiple leads per investigation

A template that accepts multiple leads investigates the relationship
between them. Pass them all in one call:

```python
cz.investigations.create_from_template(
    template_id="email-thread-investigation",
    leads=[
        {"type": "EMAIL_ADDRESS", "value": "sender@example.com"},
        {"type": "EMAIL_ADDRESS", "value": "recipient@company.com"},
        {"type": "SHA_256",       "value": "275a021..."},
    ],
)
```

## Reference scripts

- [`template_investigation.py`](../../../template_investigation.py) —
  CLI: `--list` to discover templates, then submit by `--template`
  with one or more `--lead TYPE:value` pairs.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /investigations/templates` (discovery) | responder, administrator |
| `POST /investigations` (trigger) | investigator or above |

A common deployment shape: a `responder`-role key for discovery + a
`investigator`-role key for triggering, used by separate processes.
You can also hardcode the template id from the console if discovery
isn't practical for your role.

## Troubleshooting

- **403 listing templates**: your role can't see them. Hardcode the
  template id (look it up in the console once) and skip listing.
- **400 on trigger**: usually means the lead type doesn't match
  `template.lead_types`. Re-check the template definition.
- **Investigation triggers but verdict is empty**: the time window
  may be too narrow, or the template needs additional connected data
  sources to surface activity. Check the template's expected data
  sources in the console.
