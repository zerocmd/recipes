# Getting started

The 5-minute tour. Goes from `pip install` to a working call against
your tenant.

## 1. Install

```bash
pip install -e /path/to/sdk     # editable install from a checkout
```

The SDK requires Python 3.10+. Dependencies (`httpx`, `pydantic`)
install transitively.

## 2. Get an API key

Open the Command Zero console, create a new application, and copy the
API key. Keys are bound to an **application**, and the application has
a **role** (observer / investigator / responder / administrator) that
gates which endpoints the key can reach. See
[authentication](authentication.md) for the detailed matrix.

## 3. Set environment variables

The SDK reads two env vars (with one fallback name each, for
backwards compatibility):

```bash
export COMMAND_ZERO_API="c0.your-key.here"        # was: CMDZERO_API_KEY
export COMMAND_ZERO_ORG="51c264ff-5a98-4f15-b7e1-07158d35151c"  # was: CMDZERO_ORG_ID
```

The org id can also be passed per call instead — useful for MSSPs
operating across multiple tenants. See [configuration](configuration.md).

You can also pass them as keyword arguments to the constructor:

```python
cz = CommandZero(
    api_key="c0.your-key.here",
    organization_id="51c264ff-5a98-4f15-b7e1-07158d35151c",
)
```

## 4. First call

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    print(cz.health.check())
```

Expected output:

```text
status='ok'
```

If you see `[401] unknown application key` your token is wrong. If you
see `[403] path not authorized for this role` the role lacks
permission. See [troubleshooting](troubleshooting.md).

## 5. List something

```python
with CommandZero() as cz:
    for org in cz.organizations.list():
        print(org.id, org.role, org.name)
```

`organizations.list()` returns a [`PaginatedIterator`](pagination.md)
that lazily walks pages — for one-shot consumption iterate it directly,
or call `.materialize()` to get a `list[Organization]`.

## 6. Filter

```python
pending = cz.investigations.list(
    filter="status eq 'pending-review' and severity in ('high', 'critical')",
)
for inv in pending:
    print(inv.id, inv.severity, inv.title)
```

Filter syntax is OData-flavored — see [filtering](filtering.md) for the
operator list and per-endpoint constraints. Not every documented
operator is supported on every endpoint; the page calls out the gaps
the team has hit in practice.

## 7. Mutate

```python
inv = cz.investigations.create_from_alert(
    alert_data={"sender": {"email": "x@y.com"},
                "file": {"sha256": "275a021bbfb..."}},
    alert_type="EmailMalware",
    title="Malicious attachment",
    tags=["siem"],
)
print(inv.id, inv.action)        # action == "created" or "merged"
```

Updating an existing investigation:

```python
cz.investigations.update(
    inv.id,
    status="completed",
    tags=["auto-contained", "remediated"],
)
```

Note: PATCH only accepts a subset of fields and a subset of status
transitions. See [resources/investigations](resources/investigations.md).

## Where next

- The [examples](index.md#end-to-end-use-cases) cover every blog use
  case end-to-end.
- The [resource reference](index.md#resource-reference) is a complete
  API surface listing.
- [Error handling](error-handling.md) shows the typed exception
  hierarchy you can catch.
