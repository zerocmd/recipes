# `cz.applications`

Application metadata — what integrations are configured against this
org, what role each carries, and the API key fingerprint for each.
Useful for audit and integration management.

## Endpoints

| | Method |
|---|---|
| `cz.applications.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/applications` |
| `cz.applications.get(application_id, organization_id=…)` | `GET /organizations/{org}/applications/{appId}` |

## Returns

`PaginatedIterator[Application]` and `Application`. Fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `name` | `str` | Display name set in the console |
| `role` | `str` | Open enum (see [authentication](../authentication.md)) |
| `fingerprint` | `str` | First ~8 chars of the API key (safe to log) |
| `expires_at` | `datetime \| None` | Key expiry, when set |
| `created_by` / `updated_by` | `Attribution` | |
| `created_time` / `updated_time` | `datetime` | |

## Examples

List every application configured for the current org:

```python
for app in cz.applications.list():
    print(app.id, app.role, app.fingerprint, app.name)
```

Filter by role to find all responder/admin integrations:

```python
elevated = cz.applications.list(filter="role in ('responder', 'administrator')")
```

Identify your own application by fingerprint comparison:

```python
me = next(
    (a for a in cz.applications.list()
     if a.fingerprint == "f00fee01"),
    None,
)
```

## Use it for

- **Audit logging**: enumerate every integration that can act on the org.
- **Rotation planning**: surface keys nearing `expires_at`.
- **Internal tooling**: build a UI that surfaces the integration
  topology of each tenant for support engineers.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /applications` | observer or above |
| `QUERY /applications` | varies by deployment |
| `GET /applications/{id}` | observer or above |

## Notes

- The `fingerprint` is **not secret** — it's designed to identify a
  key without exposing the secret portion. Use it in support tickets
  and audit logs.
- Application `role` is the **default** role; per-organization
  overrides surface as the `role` field on
  [`Organization`](organizations.md), not here.
