# Business context sync (HR + CMDB)

Use case: every investigation is more accurate when it knows who's a
VIP, who reports to whom, which hosts are in PCI scope, and which
boxes are production vs. staging. Push that context into Command Zero
on a periodic cadence so investigations have it before they start.

Two main feeds:

- **HR directory** — employee VIP status, department, manager chain,
  employee type.
- **CMDB** — host criticality, environment, ownership, compliance
  scope.

## One-time HR upload

```python
from cmdzero import CommandZero

records = [
    {
        "email": "sarah.kim@company.com",
        "department": "Engineering",
        "title": "VP of Engineering",
        "manager": "cto@company.com",
        "vip": True,
        "employeeType": "full-time",
    },
    {
        "email": "mike.jones@company.com",
        "department": "Finance",
        "title": "Financial Analyst",
        "manager": "cfo@company.com",
        "vip": False,
        "employeeType": "full-time",
    },
]
schema = [
    {"path": "email",   "type": "EMAIL_ADDRESS"},
    {"path": "manager", "type": "EMAIL_ADDRESS"},
]

with CommandZero() as cz:
    upload = cz.business_context.upload(
        name="HR User Directory",
        description="Employee context: VIP status, department, manager chain",
        records=records,
        schema=schema,
    )
print(upload.id, upload.status)        # "processing", becomes "ready" once indexed
```

The schema doesn't have to enumerate every record field — only the
ones that map to a catalog type. Free-form fields (`department`,
`vip`, `employeeType`) come along for the ride and are surfaced to
investigations alongside the typed fields.

## Periodic sync (the canonical pattern)

Most teams pull a fresh export from their HRIS / CMDB on a schedule
(daily, weekly) and want to **replace** the existing upload in place
rather than accumulate uploads.

```python
import os
from cmdzero import CommandZero

UPLOAD_ID = os.environ["HR_UPLOAD_ID"]    # set once at first upload

def weekly_sync():
    fresh = pull_from_workday()           # whatever your HR export looks like

    with CommandZero() as cz:
        cz.business_context.replace(
            UPLOAD_ID,
            records=fresh,
            schema=[
                {"path": "email",   "type": "EMAIL_ADDRESS"},
                {"path": "manager", "type": "EMAIL_ADDRESS"},
            ],
        )

if __name__ == "__main__":
    weekly_sync()
```

The previous version stays active for in-flight investigations until
the new data is fully processed. New investigations then use the
updated context. There's no race condition on your side — make the
call and walk away.

`records` and `schema` must be supplied together. To update only
metadata (name or description), omit them:

```python
cz.business_context.replace(UPLOAD_ID, description="Synced 2026-04-27 from Workday")
```

## CMDB upload

```python
records = [
    {
        "hostname": "db-prod-01.internal",
        "ip": "10.20.1.50",
        "environment": "production",
        "criticality": "critical",
        "complianceScope": ["pci", "sox"],
        "owner": "dba-team@company.com",
    },
    {
        "hostname": "ci-runner-04.internal",
        "ip": "10.30.4.21",
        "environment": "staging",
        "criticality": "low",
        "complianceScope": [],
        "owner": "platform@company.com",
    },
]
schema = [
    {"path": "hostname", "type": "HOST_NAME"},
    {"path": "ip",       "type": "IP_ADDRESS"},
    {"path": "owner",    "type": "EMAIL_ADDRESS"},
]

with CommandZero() as cz:
    cz.business_context.upload(
        name="CMDB Asset Inventory",
        description="Host criticality, environment, ownership, compliance scope",
        records=records,
        schema=schema,
    )
```

Now when an investigation surfaces a privilege-escalation alert
against `db-prod-01.internal`, it knows the host is in PCI scope and
the DBA team owns it from the moment it starts.

## What investigations see

Every record whose `email` (HR) or `hostname` / `ip` (CMDB) matches an
observable in an investigation is presented as enrichment context.
Investigations can read all the free-form fields in the matched
record — VIP flag, department, compliance scope — and surface them in
the summary.

## List existing uploads

```python
for u in cz.business_context.list():
    print(u.id, u.status.ljust(10), f"records={u.record_count:>6}", u.name)
```

Filter to find a specific feed:

```python
hr = next(
    cz.business_context.list(filter="contains(name, 'HR')"),
    None,
)
```

## Delete an upload

```python
cz.business_context.delete(UPLOAD_ID)
```

Deletion only affects future investigations — in-flight investigations
keep the previous data.

## Reference scripts

- [`business_context.py`](../../../business_context.py) — CLI for
  list / upload-hr / upload-cmdb / replace / delete.

## Permissions

All business-context operations typically require the
`administrator` role. See [authentication](../authentication.md).

## Notes

- `records` is `list[dict[str, Any]]` — completely free-form. Only the
  paths in `schema` are catalog-typed.
- `description` is optional on `upload(...)`.
- The Pydantic field for `schema` on the request models is `schema_`
  internally (avoiding pydantic's reserved name); on the SDK methods
  use the `schema=` kwarg.
- Records inside an upload are **not** searchable through the API —
  the list endpoint only surfaces metadata.
