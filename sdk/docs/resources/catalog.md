# `cz.catalog`

The catalog of subject types used to annotate alert payloads and
business-context records. Type IDs are upper-snake-case strings like
`EMAIL_ADDRESS`, `IP_ADDRESS`, `SHA_256`, `HOST_NAME`,
`MICROSOFT_ENTRA_USER_PRINCIPAL_NAME`.

## Endpoints

| | Method |
|---|---|
| `cz.catalog.list(filter=…, limit=…, organization_id=…)` | `GET /organizations/{org}/catalog/types` |
| `cz.catalog.get(type_id, organization_id=…)` | `GET /organizations/{org}/catalog/types/{typeId}` |
| `cz.catalog.alert_types(organization_id=…)` | shortcut for `list(filter="isAlert eq true")` |

## Returns

`PaginatedIterator[CatalogType]` and `CatalogType`. Fields:

| Field | Type | Notes |
|---|---|---|
| `id` | `str` | The upper-snake-case type identifier (`EMAIL_ADDRESS`) |
| `name` | `str` | Human-readable name (`Email Address`) |
| `description` | `str \| None` | What the type represents |
| `is_alert` | `bool` | True if this type is valid in alert schemas |
| `examples` | `list[Any]` | Sample values for documentation |
| `fields` | `list[CatalogTypeField]` | Sub-fields when the type is a structured object |
| `created_by` / `updated_by` | `Attribution \| None` | |

`CatalogTypeField`: `name`, `type`, `required`, `description`.

## Examples

List every type valid in alert schemas:

```python
for t in cz.catalog.alert_types():
    print(t.id, t.name)
```

Look up a specific type:

```python
email = cz.catalog.get("EMAIL_ADDRESS")
print(email.name)        # "Email Address"
print(email.examples)    # ["analyst@company.com", ...]
```

Filter by ID prefix to enumerate vendor-specific types:

```python
entra = cz.catalog.list(filter="startswith(id, 'MICROSOFT_ENTRA')")
```

## Use it for

- **Building alert schemas dynamically**: when integrating with a new
  SIEM, list `alert_types()` to see what type IDs are available.
- **Validation**: confirm a type ID exists before sending it in an
  alert schema or business-context upload.
- **Documentation**: surface the description and examples in your
  internal integration playbooks.

## Permissions

| Operation | Role typically required |
|---|---|
| `GET /catalog/types` | observer or above |
| `QUERY /catalog/types` | observer or above |
| `GET /catalog/types/{id}` | observer or above |

## Notes

- The catalog endpoint **does not paginate** — every type comes back
  in one response. The `next` cursor is always empty. The SDK still
  returns a `PaginatedIterator` for shape consistency.
- `MICROSOFT_ENTRA_USER` is **not** a real catalog type, despite
  appearing in some external documentation. The actual ID for an
  Entra user identifier is `MICROSOFT_ENTRA_USER_PRINCIPAL_NAME`.
- Catalog types are managed by Command Zero — applications can read
  them but cannot create or modify them.
