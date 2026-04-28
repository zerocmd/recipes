# Filtering

The Command Zero API accepts a subset of OData `$filter` syntax on
every list endpoint. The SDK passes filters through verbatim — there is
no client-side validation. This page documents what the spec promises
and where the production server actually enforces narrower rules.

## Operators

| | |
|---|---|
| Logical | `and`, `or`, `not` |
| Grouping | `(`…`)` |
| Equality | `eq`, `ne` |
| Comparison | `gt`, `ge`, `lt`, `le` |
| Set membership | `field in ('a', 'b')` |
| Array contains | `'value' in arrayField` |
| String functions | `contains(field, 'x')`, `startswith(field, 'x')`, `endswith(field, 'x')` |

String matching is **case-insensitive**. String literals use single
quotes; embed a literal quote by doubling it (`'O''Brien'`).

Comparisons can be field-to-literal (`status eq 'active'`),
literal-to-field (the operator is flipped automatically), or
field-to-field (`createdTime lt updatedTime`).

## Datatypes

| Type | Example |
|---|---|
| String | `'hello'`, `'O''Brien'` |
| Integer | `42`, `-17` |
| Float | `3.14`, `-2.5` |
| Boolean | `true`, `false` |
| Null | `null` (only valid with `eq` / `ne`) |
| DateTime | `2024-01-15T10:30:00Z` |
| Date | `2024-01-15` |
| Time | `14:30:00` |
| GUID | `550e8400-e29b-41d4-a716-446655440000` |
| Duration | `duration'P1DT2H30M'` |

## Nested paths

Use `/` (not `.`) to navigate nested object fields:

```text
createdBy/type eq 'application'
```

The grammar permits this; **whether the server accepts a given
nested path depends on the endpoint** (see "What's actually filterable"
below).

## Restrictions

The API intentionally restricts the OData spec:

- **No arithmetic** (`add`, `sub`, `mul`, `div`, `mod`).
- **No lambda expressions** (`any`, `all`).
- Only the three string functions listed above.

## What's actually filterable per endpoint

The server publishes a per-endpoint allowlist of filterable fields.
The SDK can't see that allowlist; you'll get
`400 — unknown filter field: "<name>"` for fields not in it.

This list is from production tests against a real org as of release.
It may expand or change — when in doubt, run the filter and read the
400 message.

### `/investigations`

Confirmed filterable: `status`, `severity`, `sensitivity`, `category`,
`title`, `type`, `tags` (array contains), `createdTime`, `updatedTime`,
`completedTime`, `closedTime`.

Confirmed **not** filterable (returns 400):

- `createdBy/name`, `createdBy/type`, `createdBy/id` —
  no `createdBy/*` field is filterable on this endpoint, despite the
  syntax appearing in the spec's documentation examples.
- `id` — fetch by id directly with `cz.investigations.get(id)`.
- `templateId` — not filterable here.

String functions confirmed: `contains(title, 'x')`,
`startswith(title, 'x')`.

```python
# Works
cz.investigations.list(filter="status eq 'pending-review' and severity in ('high', 'critical')")
cz.investigations.list(filter="contains(title, 'phishing')")
cz.investigations.list(filter="'vip-user' in tags and status ne 'completed'")

# Does NOT work — will raise BadRequestError
cz.investigations.list(filter="createdBy/type eq 'application'")
```

If you need to find investigations created by a specific integration,
the workaround is to **tag** them at create-time with a known marker
and filter by tag:

```python
cz.investigations.create_from_alert(
    alert_data=...,
    tags=["siem-integration", "acme-soar-v2"],
)

# Later
created_by_us = cz.investigations.list(filter="'acme-soar-v2' in tags")
```

### `/users`

Confirmed filterable: `role`, `email`, `name`.

```python
cz.users.list(filter="role ne 'observer'")     # assignable users
cz.users.list(filter="endswith(email, '@cmdzero.io')")
```

Convenience wrapper: `cz.users.assignable()`.

### `/applications`

Confirmed filterable: `role`, `name`.

### `/catalog/types`

Confirmed filterable: `isAlert` (boolean), `name`, `id`.

```python
cz.catalog.list(filter="isAlert eq true")     # types valid in alert schemas
```

Convenience wrapper: `cz.catalog.alert_types()`.

### `/remediations` and `/remediations/templates`

Filterable on remediation templates: `subjectType`, `name`,
`displayName`.

```python
cz.remediation_templates.list(filter="subjectType eq 'MICROSOFT_ENTRA_USER_PRINCIPAL_NAME'")
```

Convenience wrapper:
`cz.remediation_templates.for_subject_type("MICROSOFT_ENTRA_USER_PRINCIPAL_NAME")`.

Filterable on remediations: `status`, `templateId`, `subject/type`.

### `/context/uploads`

Filterable: `name`, `status`, `subjectTypes` (array contains).

The records inside an upload are **not** searchable through the API.

### `/investigations/templates`

Filterable: `name`, `scenario`, `severity`, `sensitivity`.

## Defensive coding

Wrap any user-supplied filter string in a single-quote escape:

```python
def safe_quote(value: str) -> str:
    return value.replace("'", "''")

filter_expr = f"contains(title, '{safe_quote(user_input)}')"
```

Or rely on the SDK helper for tags / values you control:

```python
cz.investigations.list(filter=f"'{safe_quote(tag)}' in tags")
```
