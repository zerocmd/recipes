# `cz.users`

The user directory for an organization. The endpoint you hit before
assigning an investigation to an analyst.

## Endpoints

| | Method |
|---|---|
| `cz.users.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/users` |
| `cz.users.get(user_id, organization_id=…)` | `GET /organizations/{org}/users/{userId}` |
| `cz.users.assignable(organization_id=…)` | shortcut for `list(filter="role ne 'observer'")` |

## Returns

`PaginatedIterator[User]` and `User`. Fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | Pass to `cz.investigations.update(assignees=[user_id])` |
| `email` | `str \| None` | |
| `name` | `str \| None` | Display name |
| `role` | `str` | Open enum (`observer`, `investigator`, `responder`, `administrator`) |
| `created_by` / `updated_by` | `Attribution \| None` | |
| `created_time` / `updated_time` | `datetime \| None` | |

## Examples

Anyone who can take action on an investigation:

```python
for u in cz.users.assignable():
    print(u.id, u.role, u.email)
```

Find a user by email:

```python
user = next(
    (u for u in cz.users.list(filter="email eq 'analyst@company.com'")),
    None,
)
if user:
    cz.investigations.update(inv_id, assignees=[user.id])
```

Filter by role:

```python
responders = cz.users.list(filter="role eq 'responder'")
```

Substring match on name (case-insensitive):

```python
matches = cz.users.list(filter="contains(name, 'kim')")
```

## Use it for

- **Auto-assignment**: pick an analyst based on rotation, expertise, or
  load and PATCH the investigation's `assignees`.
- **Routing**: in MSSP setups, route investigations to the responder
  responsible for that tenant's coverage.
- **Notifications**: build the recipient list for a Slack message
  about a new high-severity investigation.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /users` | observer or above |
| `QUERY /users` | administrator (varies by deployment) |
| `GET /users/{id}` | observer or above |

The `assignable()` convenience uses GET.

## Notes

- `role` is an open enum — production may return capitalized
  variants (`'Investigators'`) where the docs claim lowercase.
  Compare case-insensitively if your code branches on role:
  `if u.role and u.role.lower().startswith('investigator'): ...`
- Assigning an investigation: PATCH `/investigations/{id}` accepts a
  list of user UUIDs, not user objects:
  `cz.investigations.update(inv_id, assignees=[user.id, user2.id])`.
- Setting `assignees=[]` clears the assignee list entirely.
