# Command Zero Python SDK

A typed, sync Python client for the Command Zero Public API.

- **Endpoints:** every documented endpoint of the public API (v2026-03-12)
- **Models:** Pydantic v2 with snake↔camel aliasing, forward-compatible (`extra='allow'`)
- **Transport:** `httpx` with bearer auth, automatic 429 retry+backoff, trace-id capture
- **Errors:** typed exception hierarchy mapped to HTTP status codes
- **Pagination:** lazy iterators that walk every page

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    health = cz.health.check()
    for inv in cz.investigations.list(filter="severity eq 'high'"):
        print(inv.id, inv.status, inv.title)
```

---

## Install

```bash
pip install -e .
# or, from a checkout that lives elsewhere
pip install /path/to/sdk
```

Requirements: Python 3.10+, `httpx>=0.27`, `pydantic>=2.5`.

## Authenticate

The SDK reads two environment variables:

| Variable | Purpose | Fallback |
|---|---|---|
| `COMMAND_ZERO_API` | API key (Bearer token) | `CMDZERO_API_KEY` |
| `COMMAND_ZERO_ORG` | Default organization id | `CMDZERO_ORG_ID` |

Or pass them directly:

```python
cz = CommandZero(
    api_key="c0.your-key.here",
    organization_id="51c264ff-5a98-4f15-b7e1-07158d35151c",
)
```

API keys are created in the Command Zero console and bound to an
**application** with a role: `observer`, `investigator`, `responder`, or
`administrator`. The role determines which endpoints the key can reach;
unauthorized calls raise [`ForbiddenError`](docs/error-handling.md). See
[authentication](docs/authentication.md) for the full matrix.

## Quick start

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    # confirm the key works
    cz.health.check()                          # HealthResponse(status='ok')

    # what orgs can this key see?
    for org in cz.organizations.list():
        print(org.id, org.role, org.name)

    # who can be assigned an investigation?
    for u in cz.users.assignable():
        print(u.email, u.role)

    # high-severity investigations awaiting review
    pending = cz.investigations.list(
        filter="status eq 'pending-review' and severity in ('high', 'critical')",
    )
    for inv in pending:
        print(inv.id, inv.severity, inv.title)
```

Every list method returns a [`PaginatedIterator`](docs/pagination.md)
that lazily fetches pages as you consume them.

## Resources

The client exposes one attribute per resource group. Each has a small,
predictable surface (`list`, `get`, `create`, `update`, `delete` where
applicable).

| Attribute | Backs | Reference |
|---|---|---|
| `cz.health` | `GET /ok` | [health](docs/resources/health.md) |
| `cz.organizations` | `/organizations` | [organizations](docs/resources/organizations.md) |
| `cz.applications` | `/applications` | [applications](docs/resources/applications.md) |
| `cz.users` | `/users` | [users](docs/resources/users.md) |
| `cz.catalog` | `/catalog/types` | [catalog](docs/resources/catalog.md) |
| `cz.business_context` | `/context/uploads` | [business-context](docs/resources/business-context.md) |
| `cz.investigation_templates` | `/investigations/templates` | [investigation-templates](docs/resources/investigation-templates.md) |
| `cz.investigations` | `/investigations` | [investigations](docs/resources/investigations.md) |
| `cz.remediation_templates` | `/remediations/templates` | [remediation-templates](docs/resources/remediation-templates.md) |
| `cz.remediations` | `/remediations` | [remediations](docs/resources/remediations.md) |

## Common patterns

### Filtering

The API accepts an OData-style subset. Filters can be passed to any
`list()` call:

```python
cz.investigations.list(filter="status eq 'pending-review'")
cz.investigations.list(filter="severity in ('high', 'critical')")
cz.investigations.list(filter="contains(title, 'phishing')")
cz.investigations.list(filter="'vip-user' in tags and status ne 'completed'")
```

See [filtering](docs/filtering.md) for the full operator list **and the
fields actually filterable per endpoint** — the OData grammar is broader
than what the server accepts. Filtering by `createdBy/*` paths, for
example, is rejected on `/investigations` even though the syntax is
documented.

### Pagination

```python
for inv in cz.investigations.list(filter="severity eq 'high'", limit=200):
    process(inv)               # one HTTP call per page, transparently

# or grab everything as a list
rows = cz.investigations.list(filter="status eq 'pending-review'").materialize()
```

Pagination always uses **GET** by default (broadest role compatibility).
Pass `method='QUERY'` if you need to send a complex filter that exceeds
safe URL length. See [pagination](docs/pagination.md).

### Errors

Every API failure raises a typed subclass of `CommandZeroError`. The
trace id from the response header is preserved on every exception:

```python
from cmdzero import CommandZero, NotFoundError, ForbiddenError, RateLimitError

with CommandZero() as cz:
    try:
        cz.investigations.get("00000000-0000-0000-0000-000000000000")
    except NotFoundError as e:
        log.warning("missing investigation, trace=%s", e.trace_id)
    except ForbiddenError as e:
        log.error("role lacks permission, trace=%s body=%s", e.trace_id, e.body)
    except RateLimitError as e:
        log.warning("throttled, retry_after=%ss trace=%s", e.retry_after, e.trace_id)
```

See [error-handling](docs/error-handling.md) for the full hierarchy.

### Postbacks

Many operations (start-investigation, create-remediation) accept a
postback URL — Command Zero will POST the completion payload to that
URL with the bearer token you provided:

```python
cz.investigations.create_from_alert(
    alert_data=...,
    postback={"url": "https://soar.internal/cb", "token": "shared-secret"},
)
```

The payload shapes are modeled as
[`InvestigationPostbackPayload`](docs/resources/investigations.md) and
[`RemediationPostbackPayload`](docs/resources/remediations.md). See
[postbacks](docs/postbacks.md) for a Flask receiver template.

## Examples

End-to-end walkthroughs of every public-API use case:

| Use case | Walkthrough |
|---|---|
| Alert-triggered investigations from a SIEM/SOAR | [examples/alert-ingestion](docs/examples/alert-ingestion.md) |
| Template-based investigations (HR last-day, separation reviews) | [examples/template-investigations](docs/examples/template-investigations.md) |
| Business context (HR + CMDB) sync with replace workflow | [examples/business-context-sync](docs/examples/business-context-sync.md) |
| Automated remediation after investigation verdict | [examples/automated-remediation](docs/examples/automated-remediation.md) |
| Investigation pipeline visibility & SLA tracking | [examples/pipeline-reporting](docs/examples/pipeline-reporting.md) |
| MSSP / multi-tenant operations across orgs | [examples/mssp-multi-tenant](docs/examples/mssp-multi-tenant.md) |

## Configuration

| Variable | Default | Notes |
|---|---|---|
| `COMMAND_ZERO_API` | — | Required (or pass `api_key=`). |
| `COMMAND_ZERO_ORG` | — | Optional default org id (or pass per call). |
| `CMDZERO_API_BASE` | `https://api.cmdzero.io/public/v1` | Override for non-prod environments. |

Constructor knobs: `timeout`, `max_retries`, `user_agent`, `client` (BYO
`httpx.Client`). See [configuration](docs/configuration.md).

## Compatibility

| | Version |
|---|---|
| Python | 3.10, 3.11, 3.12, 3.13 |
| Command Zero API | v2026-03-12 |
| `httpx` | ≥ 0.27 |
| `pydantic` | ≥ 2.5 |

The SDK uses `extra='allow'` on every model so new server fields
deserialize without raising. Open enums (status, role) are typed as
`str` so unknown future values pass through; the corresponding
`StrEnum` classes ([cmdzero/enums.py](cmdzero/enums.py)) remain
exported as ergonomic constants.

## Versioning & changelog

This SDK follows [SemVer](https://semver.org/). See
[CHANGELOG](CHANGELOG.md).

## License

Proprietary. See [LICENSE](LICENSE).

## Support

Every API error carries an `X-Cmdzero-Traceid` header — the SDK exposes
it as `error.trace_id` on every raised exception. Include it in any
support conversation. See [troubleshooting](docs/troubleshooting.md)
for common failure modes.
