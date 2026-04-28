# `cz.business_context`

Upload structured data about subjects in your environment so
investigations can enrich their findings without re-querying your IT
systems each time. Two main feeds: **HR directory** (VIP, department,
manager chain, employee type) and **CMDB** (asset criticality,
environment, ownership, compliance scope).

## Endpoints

| | Method |
|---|---|
| `cz.business_context.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/context/uploads` |
| `cz.business_context.get(upload_id, organization_id=…)` | `GET /organizations/{org}/context/uploads/{id}` |
| `cz.business_context.upload(name=, records=, schema=, description=, organization_id=…)` | `POST /organizations/{org}/context/uploads` |
| `cz.business_context.replace(upload_id, name=, description=, records=, schema=, organization_id=…)` | `PUT /organizations/{org}/context/uploads/{id}` |
| `cz.business_context.delete(upload_id, organization_id=…)` | `DELETE /organizations/{org}/context/uploads/{id}` |

## Returns

Most calls return `BusinessContextUpload`. Fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | |
| `organization_id` | `UUID` | |
| `name` | `str` | |
| `description` | `str` | |
| `record_count` | `int` | How many records were ingested |
| `status` | `BusinessContextStatus` | `processing` \| `ready` \| `failed` |
| `subject_types` | `list[str]` | Catalog type IDs that the records map to |
| `error` | `str` | Empty unless `status='failed'` |
| `created_by` / `updated_by` | `Attribution` | |
| `created_time` / `updated_time` | `datetime` | |

`status='processing'` is returned immediately after a POST or PUT —
the upload becomes `'ready'` once Command Zero has indexed the records.
Records inside an upload are **not** searchable through the API; this
endpoint only returns metadata.

## Schema annotations

Every upload pairs `records` (an arbitrary JSON object array) with a
`schema` that maps JSON paths to catalog type IDs. Example for an HR
feed:

```python
schema = [
    {"path": "email",   "type": "EMAIL_ADDRESS"},
    {"path": "manager", "type": "EMAIL_ADDRESS"},
]
```

The `path` uses dots for nested objects. Use
[`cz.catalog`](catalog.md) to look up valid type IDs.

## Examples

Upload an HR directory:

```python
records = [
    {
        "email": "sarah.kim@company.com",
        "department": "Engineering",
        "title": "VP of Engineering",
        "manager": "cto@company.com",
        "vip": True,
        "employeeType": "full-time",
    },
    # ... more records
]
schema = [
    {"path": "email",   "type": "EMAIL_ADDRESS"},
    {"path": "manager", "type": "EMAIL_ADDRESS"},
]

upload = cz.business_context.upload(
    name="HR User Directory",
    description="Employee context: VIP status, department, manager chain",
    records=records,
    schema=schema,
)
print(upload.id, upload.status)        # "processing"
```

Upload a CMDB:

```python
records = [
    {
        "hostname": "db-prod-01.internal",
        "ip": "10.20.1.50",
        "environment": "production",
        "criticality": "critical",
        "complianceScope": ["pci", "sox"],
        "owner": "dba-team@company.com",
    },
]
schema = [
    {"path": "hostname", "type": "HOST_NAME"},
    {"path": "ip",       "type": "IP_ADDRESS"},
    {"path": "owner",    "type": "EMAIL_ADDRESS"},
]
cz.business_context.upload(name="CMDB Snapshot", records=records, schema=schema)
```

Periodic resync — replace the dataset in place:

```python
# Weekly cron pulls a fresh export and replaces the same upload id
fresh_records = pull_from_hris()
cz.business_context.replace(
    "u-existing-id",
    records=fresh_records,
    schema=schema,
)
```

The previous version stays active for in-flight investigations until
the new data is fully processed; new investigations then use the
updated context. Records and schema must be supplied together.

Metadata-only update (no records change):

```python
cz.business_context.replace("u-existing-id", description="updated weekly via Workday export")
```

Delete an upload:

```python
cz.business_context.delete("u-existing-id")
```

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /context/uploads` | administrator |
| `POST /context/uploads` | administrator |
| `PUT /context/uploads/{id}` | administrator |
| `DELETE /context/uploads/{id}` | administrator |

Business context is administrator-gated in most deployments because it
shapes how every future investigation interprets identities and
assets.

## Filtering

Filterable fields on the list endpoint: `name`, `status`,
`subjectTypes` (array contains).

```python
cz.business_context.list(filter="'EMAIL_ADDRESS' in subjectTypes and status eq 'ready'")
```

## Notes

- The Pydantic field for `schema` is `schema_` in Python (to avoid
  pydantic's reserved name) but serializes to `schema` on the wire —
  use the `schema=` kwarg on the SDK methods, not `schema_`.
- See [examples/business-context-sync](../examples/business-context-sync.md)
  for a complete weekly-sync pattern.
