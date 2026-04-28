# Authentication

Every Command Zero API call is authenticated with an **API key** issued
to an **application** in your console. The key is sent as a bearer
token in the `Authorization` header. The SDK handles that for you.

```python
from cmdzero import CommandZero

cz = CommandZero(api_key="c0.your-key.here")
# Authorization: Bearer c0.your-key.here  is added automatically
```

## Key rotation

API keys can be rotated in the console. The first ~16 characters
(before the second period, e.g. `c0.f00fee.`) are the **fingerprint** —
not secret, safe to log and share with support. The full key is secret.

To check what fingerprint your key currently has:

```python
me = cz.applications.list().materialize()       # returns this app + others
print(me[0].fingerprint)
```

## Application roles

Each application is assigned one of four roles. The role determines
which endpoints the API key can reach. Unauthorized calls raise
[`ForbiddenError`](error-handling.md) (HTTP 403).

| Role | Typical use | Investigations | Remediations | Business context | Templates |
|---|---|:-:|:-:|:-:|:-:|
| `observer` | Read-only dashboards | read | none | none | read |
| `investigator` | SIEM/SOAR integrations | read + create | none | none | read |
| `responder` | Containment automation | read + create + update | read + create | none | read |
| `administrator` | Full integration | full | full | full | full |

This matrix is approximate — exact path-by-path policy is enforced
server-side and may vary per tenant. A 403 from any endpoint means
**the binding application's role policy doesn't include that path**;
talk to your Command Zero admin to upgrade the role or move the
operation to a key with broader access.

## Method-level role policy

Role policy is enforced **per (HTTP method, path) pair**, not just per
path. In practice this means a role may allow `GET /users` but reject
`QUERY /users` even though both list users.

The SDK's pagination defaults to `GET` for that reason — see
[pagination](pagination.md). Pass `method='QUERY'` only when you need
to send a filter that's too long to fit in the URL.

## Multi-tenant (MSSP)

A single API key bound to an application can have access to multiple
organizations. Discover them with:

```python
for org in cz.organizations.list():
    print(org.id, org.role, org.name)
```

Then call any resource per-org by passing `organization_id=...`:

```python
for org in cz.organizations.list():
    invs = cz.investigations.list(filter="status eq 'pending-review'",
                                  organization_id=org.id)
    print(org.name, sum(1 for _ in invs))
```

See [examples/mssp-multi-tenant](examples/mssp-multi-tenant.md).

## What the SDK reads from the environment

| Variable | Purpose | Fallback |
|---|---|---|
| `COMMAND_ZERO_API` | Bearer token | `CMDZERO_API_KEY` |
| `COMMAND_ZERO_ORG` | Default org id | `CMDZERO_ORG_ID` |
| `CMDZERO_API_BASE` | Base URL | (defaults to production) |

The SDK does **not** auto-load `.env` files — that's an application
concern. The example scripts at the project root use `python-dotenv`
to load `.env` before constructing the client.

## Security notes

- Never commit your key to source control. The included
  [`.gitignore`](../../.gitignore) excludes `.env`.
- Don't log the full key. Log the fingerprint instead.
- Don't pass the key in URL query params. The SDK never does.
- Postback tokens are independent secrets used to authenticate
  callbacks **from** Command Zero **to** your service — see
  [postbacks](postbacks.md).
