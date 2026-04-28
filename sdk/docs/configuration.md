# Configuration

`CommandZero(...)` accepts these constructor knobs. Every one of them
also has an environment-variable equivalent for app-level configuration.

## Constructor

```python
CommandZero(
    api_key: str | None = None,                # COMMAND_ZERO_API
    *,
    organization_id: str | UUID | None = None, # COMMAND_ZERO_ORG
    base_url: str | None = None,               # CMDZERO_API_BASE
    timeout: float | None = None,              # default 30.0 seconds
    max_retries: int | None = None,            # default 5 (429s only)
    client: httpx.Client | None = None,        # BYO client
    user_agent: str | None = None,             # default "cmdzero-python-sdk/0.1.0"
)
```

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `COMMAND_ZERO_API` | _none_ (required) | API key sent as `Authorization: Bearer …` |
| `COMMAND_ZERO_ORG` | _none_ | Default organization id; per-call `organization_id=` overrides |
| `CMDZERO_API_BASE` | `https://api.cmdzero.io/public/v1` | Override for staging/dev environments |
| `CMDZERO_API_KEY` | — | Backwards-compat fallback for `COMMAND_ZERO_API` |
| `CMDZERO_ORG_ID` | — | Backwards-compat fallback for `COMMAND_ZERO_ORG` |

The SDK does not auto-load `.env`. If you want that, pull in
[`python-dotenv`](https://pypi.org/project/python-dotenv/) at app
startup:

```python
from dotenv import load_dotenv
load_dotenv()

from cmdzero import CommandZero       # now sees COMMAND_ZERO_API
cz = CommandZero()
```

## Timeouts

`timeout=30.0` is the per-request floor (connect + read). Increase it
for endpoints that issue large queries:

```python
cz = CommandZero(timeout=120.0)
```

For finer control, build your own `httpx.Client` and pass it via
`client=`:

```python
import httpx
client = httpx.Client(
    timeout=httpx.Timeout(connect=5.0, read=120.0, write=30.0, pool=5.0),
)
cz = CommandZero(client=client)
```

When you pass `client=`, the SDK does **not** close it on `cz.close()`
— you own its lifecycle.

## Retries

The transport retries on `429 Too Many Requests` only, with
exponential backoff that honors the `Retry-After` header when present.
Defaults: `max_retries=5`, base 1s, cap 30s.

```python
cz = CommandZero(max_retries=10)        # patient batch jobs
cz = CommandZero(max_retries=1)         # interactive paths that should fail fast
```

Other 4xx and 5xx responses raise immediately — see
[error-handling](error-handling.md). 5xx is **not** retried because
mutating endpoints (POST `/investigations`, POST `/remediations`) are
not idempotent and a blind retry could double-submit.

## Per-call overrides

Most resource methods accept an `organization_id=` argument that takes
precedence over `CommandZero(organization_id=...)`. Useful for MSSPs:

```python
cz = CommandZero()                              # no default org
for org in cz.organizations.list():
    cz.investigations.list(organization_id=org.id, filter="severity eq 'critical'")
```

## Custom user agent

Tag your traffic so it's visible in support investigations:

```python
cz = CommandZero(user_agent="acme-soar/2.4.1 (cmdzero-python-sdk/0.1.0)")
```

Server-side request logs key off `User-Agent`; tagging makes
"who is hammering us right now?" answerable in seconds.

## Lifecycle

The client owns an `httpx.Client` (unless you supplied one). Close it
explicitly to release the connection pool:

```python
cz = CommandZero()
try:
    ...
finally:
    cz.close()
```

Or use the context-manager form:

```python
with CommandZero() as cz:
    ...
```

The SDK is safe to share across threads; do not share across
processes (HTTP/2 connections in `httpx.Client` are per-process).
