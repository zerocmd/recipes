# `cz.investigations`

The core of the API. Start investigations from raw alert data or from
named templates, retrieve status and results, list and filter across
the org, and update metadata (status, assignees, tags, severity).

## Endpoints

| | Method |
|---|---|
| `cz.investigations.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/investigations` |
| `cz.investigations.get(investigation_id, organization_id=…)` | `GET /organizations/{org}/investigations/{id}` |
| `cz.investigations.create(request, nosettle=False, organization_id=…)` | `POST /organizations/{org}/investigations` |
| `cz.investigations.create_from_alert(alert_data=, alert_type=…, alert_schema=…, …)` | `POST …` (alert form) |
| `cz.investigations.create_from_template(template_id, leads, …)` | `POST …` (template form) |
| `cz.investigations.update(investigation_id, …, organization_id=…)` | `PATCH /organizations/{org}/investigations/{id}` |

## Returns

`Investigation` (or `CreateInvestigationResponse` from POST, which
extends `Investigation` with an `action` field). The most useful
fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `UUID` | |
| `organization_id` | `UUID` | |
| `title` | `str` | |
| `description` | `str \| None` | |
| `type` | `str \| None` | `'alert'` \| `'template'` \| `'manual'` |
| `status` | `str` | open enum: `investigating`, `pending-review`, `in-progress`, `on-hold`, `completed`, `failed` |
| `severity` | `str \| None` | known: `critical`/`high`/`medium`/`low`/`informational` (case may vary) |
| `sensitivity` | `str \| None` | TLP-style: `red`/`strict`/`amber`/`green`/`clear` |
| `confidence_level` | `str \| None` | `high` / `moderate` / `low` |
| `impact` | `str \| None` | same scale as severity |
| `category` | `str \| None` | e.g. `BUSINESS-EMAIL-COMPROMISE-(BEC)` |
| `verdict` | `list[str]` | one or more verdict tags |
| `summary` | `str \| None` | Markdown — the analyst-facing writeup |
| `observables` | `list[Observable]` | Atoms of intelligence found by the investigation |
| `assignees` | `list[UserReference]` | |
| `tags` | `list[str]` | |
| `template_id` | `str \| None` | Set when `type='template'` |
| `start_time` / `end_time` | `datetime \| None` | Investigation window |
| `created_time` / `completed_time` / `closed_time` | `datetime \| None` | SLA timestamps |
| `created_by` / `updated_by` | `Attribution` | |
| `console_url` | `str \| None` | Direct link into the Command Zero UI |
| `alerts` | `list[InvestigationAlertEntry] \| None` | Set when `type='alert'` |

`CreateInvestigationResponse` adds:

- `action`: `'created'` (new investigation) or `'merged'` (rolled into
  an existing related investigation per Command Zero's grouping logic)

## Creating from an alert

Three input shapes are supported:

### Form 1: built-in alert type

If Command Zero already has a schema registered for your alert source
(CrowdStrike, Recorded Future, etc.), pass `alert_type` and
`alert_data`:

```python
inv = cz.investigations.create_from_alert(
    alert_data={
        "sender": {"email": "badactor@example.com"},
        "file": {"sha256": "275a021bbfb..."},
        "seen": "2026-01-13T15:00:00Z",
    },
    alert_type="EmailMalware",
    title="Malicious attachment detected",
    tags=["siem-integration"],
    postback={"url": "https://soar/cb", "token": "shh"},
)
print(inv.id, inv.action)         # action: 'created' or 'merged'
```

### Form 2: alert type + inline schema

If Command Zero doesn't have a built-in schema for your source,
provide the type annotations inline:

```python
inv = cz.investigations.create_from_alert(
    alert_data={
        "sender": {"email": "x@y.com"},
        "file": {"sha256": "275a021..."},
    },
    alert_type="CustomEmailAlert",
    alert_schema=[
        {"path": "sender.email", "type": "EMAIL_ADDRESS"},
        {"path": "file.sha256",  "type": "SHA_256"},
    ],
)
```

### Form 3: catalog-type schema string

If your alert is essentially a single catalog type, pass the type ID
as `alert_schema` and omit `alert_type`:

```python
inv = cz.investigations.create_from_alert(
    alert_data={"address": "suspicious@example.com"},
    alert_schema="EMAIL_ADDRESS",
)
```

### `nosettle`

Pass `nosettle=True` to return immediately and have Command Zero
process the alert asynchronously. The default is to wait until the
investigation has been registered before responding.

## Creating from a template

Pass the template id and a list of leads:

```python
inv = cz.investigations.create_from_template(
    template_id="users-last-day",
    leads=[{"type": "EMAIL_ADDRESS", "value": "departing.employee@company.com"}],
    title="Last day review — J. Smith",
    start_time=datetime(2026, 4, 1, tzinfo=timezone.utc),
    end_time=datetime(2026, 4, 27, tzinfo=timezone.utc),
)
```

Each lead is `{type: <catalog-type-id>, value: <whatever>}`. The
template's `lead_types` field tells you what types it accepts.

## Updating

PATCH accepts a small fixed set of fields. Arrays **fully replace**
the existing value (pass `tags=[]` to clear).

| Field | Type | Notes |
|---|---|---|
| `assignees` | `list[UUID]` | User ids; `[]` clears |
| `category` | `str` | |
| `description` | `str` | maxLength 5000 |
| `sensitivity` | `'red'` \| `'strict'` \| `'amber'` \| `'green'` \| `'clear'` | |
| `severity` | `'critical'` \| `'high'` \| `'medium'` \| `'low'` \| `'informational'` | |
| `status` | `'in-progress'` \| `'on-hold'` \| `'completed'` | client-settable subset only |
| `tags` | `list[str]` | `[]` clears |
| `title` | `str` | maxLength 500 |

```python
cz.investigations.update(
    inv.id,
    status="completed",
    tags=["auto-contained", "remediated", "credential-compromise"],
)
```

### Status transitions

The server enforces these rules:

| From | Permitted to |
|---|---|
| `pending-review` | `in-progress`, `on-hold`, `completed` |
| `in-progress` | `on-hold`, `completed` |
| `on-hold` | `in-progress`, `completed` |
| `investigating`, `completed`, `failed` | (terminal — illegal to change) |

`'investigating'` (automation-only) and `'failed'` (system-only) cannot
be set by the client. Illegal transitions raise
`UnprocessableEntityError` (HTTP 422).

## Listing & filtering

```python
# High-severity work awaiting review
pending = cz.investigations.list(
    filter="status eq 'pending-review' and severity in ('high', 'critical')",
)

# Anything tagged for a specific campaign
tagged = cz.investigations.list(filter="'apt-campaign-2026' in tags")

# Substring on title
phishing = cz.investigations.list(filter="contains(title, 'phishing')")

# By time
recent = cz.investigations.list(filter="createdTime ge 2026-04-01T00:00:00Z")
```

Filterable fields: `status`, `severity`, `sensitivity`, `category`,
`title`, `type`, `tags`, `createdTime`, `updatedTime`, `completedTime`,
`closedTime`. **Not** filterable: `id`, `templateId`, `createdBy/*`.
See [filtering](../filtering.md).

## Use it for

- **SIEM/SOAR alert ingestion**: form-1 / form-2 / form-3 above.
- **HR / IAM workflows**: template-based investigations triggered by
  separation events, dormant-account flags, etc.
- **Operational reporting**: `list()` with filters powers the
  pipeline-visibility patterns in
  [examples/pipeline-reporting](../examples/pipeline-reporting.md).
- **Auto-close after remediation**: PATCH to
  `status='completed'` with outcome tags.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /investigations` | observer or above |
| `QUERY /investigations` | observer or above |
| `POST /investigations` | investigator or above |
| `GET /investigations/{id}` | observer or above |
| `PATCH /investigations/{id}` | investigator or above |

## Notes

- The `alerts` field on the response is only populated when `type='alert'`.
- The `merged` action means Command Zero detected this alert relates
  to an in-flight investigation and rolled it in. Don't open a
  duplicate ticket on your side; reference the existing
  `investigation_id`.
- The `summary` field is Markdown — render it as such in your
  ticketing system.
- The full `Investigation` object can be ~50 fields after
  populated. Use `inv.model_dump(by_alias=True, exclude_none=True)`
  to get a JSON-friendly dict for downstream systems.
