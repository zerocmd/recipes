# MSSP / multi-tenant

Use case: an MSSP integration that operates across many customer
organizations from a single API key. Or any deployment where the same
application is bound to more than one org.

The API is **org-scoped throughout** — every endpoint (except `/ok`
and `/organizations`) takes an organization id. The `/organizations`
endpoint is the discovery mechanism.

## Discover orgs

```python
from cmdzero import CommandZero

with CommandZero() as cz:                # no default org
    orgs = list(cz.organizations.list())
    print(f"{len(orgs)} accessible org(s)")
    for org in orgs:
        print(f"  {org.id}  role={org.role:<14}  {org.name}")
```

Each `Organization` carries a `role` field — this application's role
**in that specific org**. An app can be `investigator` in one tenant
and `responder` in another.

## Per-org operations

Pass `organization_id=` to override the client's default:

```python
with CommandZero() as cz:                # again, no default org
    for org in cz.organizations.list():
        pending = cz.investigations.list(
            filter="status eq 'pending-review' and severity in ('high', 'critical')",
            organization_id=org.id,
        )
        n = sum(1 for _ in pending)
        if n:
            log.info("%s: %d high-sev pending review", org.name, n)
```

Equivalent pattern with a per-org client (each constructed once):

```python
with CommandZero() as discovery:
    orgs = list(discovery.organizations.list())

for org in orgs:
    with CommandZero(organization_id=org.id) as cz:
        for inv in cz.investigations.list(filter="status eq 'pending-review'"):
            ...
```

The single-client pattern is simpler; the per-client pattern can be
cleaner when each org's processing runs in a separate worker and
shouldn't share the connection pool.

## Routing investigations to per-tenant analysts

Combine `cz.users.assignable(organization_id=…)` with
`cz.investigations.update(organization_id=…)` to route per-tenant:

```python
def auto_assign(cz, org_id, investigation_id):
    candidates = list(cz.users.assignable(organization_id=org_id))
    if not candidates:
        log.warning("no assignable users in org %s", org_id)
        return
    chosen = pick_least_loaded(candidates)        # your routing logic
    cz.investigations.update(
        investigation_id,
        assignees=[chosen.id],
        organization_id=org_id,
    )
```

## Per-tenant business context

Each tenant has its own catalog of business-context uploads. Push
HR/CMDB feeds per-tenant:

```python
for org in cz.organizations.list():
    if org.role not in ("administrator",):    # business context typically requires admin
        continue
    cz.business_context.replace(
        upload_id=tenant_upload_ids[org.id],
        records=hr_export_for(org.name),
        schema=[{"path": "email", "type": "EMAIL_ADDRESS"}],
        organization_id=org.id,
    )
```

## Cross-tenant rollup reporting

For an MSSP NOC dashboard, fan out:

```python
from collections import Counter

def rollup(cz):
    summary = []
    for org in cz.organizations.list():
        by_sev = Counter()
        for inv in cz.investigations.list(
            filter="status eq 'pending-review'",
            organization_id=org.id,
        ):
            by_sev[(inv.severity or "unknown").lower()] += 1
        summary.append({
            "org_id": str(org.id),
            "org_name": org.name,
            "role": org.role,
            "pending_critical": by_sev["critical"],
            "pending_high": by_sev["high"],
            "pending_medium": by_sev["medium"],
            "pending_total": sum(by_sev.values()),
        })
    return summary
```

For very large tenant counts, parallelize per-org calls with a
`ThreadPoolExecutor` — `httpx.Client` is thread-safe.

## Reference scripts

- [`mssp_multi_tenant.py`](../../../mssp_multi_tenant.py) — CLI with
  `summary` (per-org open-investigation + user counts) and
  `assignable-users` (full assignable-user listing per tenant).

## Permissions

The application's role can vary per tenant. Reading the `role` field
on each `Organization` lets your code branch on what's possible:

```python
for org in cz.organizations.list():
    if org.role == "observer":
        # read-only path
        ...
    elif org.role in ("responder", "administrator"):
        # full path including remediation
        ...
```

## Performance & scale

- The client is thread-safe; spread per-tenant work across a
  thread pool when the tenant count is high.
- Each org has its own rate-limit budget. Bursty traffic to one
  tenant won't starve the others.
- Cache the org list — it changes rarely. Refresh on a schedule, not
  per-request.
- Tag log lines with the `org.id` to make per-tenant debugging easy.

## Notes

- The bound application's `role` may be `'observer'` in some orgs and
  `'investigator'` (or higher) in others. Don't assume uniform.
- Don't share an org id across tenants in any code path — every API
  call must be scoped to exactly one tenant.
