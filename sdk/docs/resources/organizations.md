# `cz.organizations`

Lists organizations the bound application can act against. The
discovery endpoint for multi-tenant integrations.

## Endpoints

| | Method | Notes |
|---|---|---|
| `cz.organizations.list(filter=…, limit=…)` | `GET /organizations` | The default; broadest role compatibility |

## Returns

`PaginatedIterator[Organization]`. The `Organization` model:

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | Pass to other resources as `organization_id=` |
| `name` | `str` | Human-readable tenant name |
| `role` | `str` | The application's role in this org (open enum; see [authentication](../authentication.md)) |
| `created_by` / `updated_by` | `Attribution` | Who/what created or last touched the org record |
| `created_time` / `updated_time` | `datetime` | |

## Examples

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    for org in cz.organizations.list():
        print(org.id, org.role, org.name)
```

Filter by role:

```python
admin_orgs = cz.organizations.list(filter="role eq 'administrator'")
```

Iterate per-org and call other resources:

```python
for org in cz.organizations.list():
    pending = cz.investigations.list(
        filter="status eq 'pending-review'",
        organization_id=org.id,
    )
    n = sum(1 for _ in pending)
    print(f"{org.name}: {n} pending")
```

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /organizations` | any role with at least one org assignment |
| `QUERY /organizations` | administrator (varies by deployment) |

The SDK defaults to GET, so most roles can list orgs. To use QUERY for
long filter expressions, pass `method='QUERY'` and have an admin role.

## Notes

- This is the only resource that doesn't take an organization id —
  it's how you find them in the first place.
- An application can have **different roles in different orgs**. The
  `role` field on each `Organization` reflects the role for that
  specific tenant.
- See [examples/mssp-multi-tenant](../examples/mssp-multi-tenant.md)
  for the canonical multi-tenant pattern.
