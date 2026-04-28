# `cz.health`

API health and authentication probe. The single endpoint here doubles
as a credential check — a 200 confirms the bearer token is valid.

## Endpoints

| | Method |
|---|---|
| `cz.health.check()` | `GET /ok` |

## Returns

`HealthResponse(status='ok')`. Any other status code raises a typed
`CommandZeroError` (typically `UnauthorizedError` for 401 or
`ForbiddenError` for 403).

## Example

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    h = cz.health.check()
    print(h.status)        # "ok"
```

## Use it for

- **Pre-flight checks** in your SOAR playbook: confirm the key works
  before submitting an alert.
- **Uptime monitoring**: a single GET that returns quickly. Useful
  signal for synthetic checks.
- **Debugging** integration failures: rules out the credential as a
  cause when narrowing down a problem.

## Permissions

Every role can hit this endpoint.

## Notes

- This endpoint is **not** scoped to an organization — `/ok` is at the
  base of the API, not under `/organizations/{org}/`.
- A 200 response confirms the token is valid; it does not tell you
  what role or permissions the token has. Use
  [`cz.applications.list()`](applications.md) for that.
