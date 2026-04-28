# Changelog

All notable changes to this project are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); the SDK adheres
to [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] — 2026-04-27

Initial release. Covers every documented endpoint of the Command Zero
Public API v2026-03-12.

### Added

- `CommandZero` top-level client with one attribute per resource group:
  `health`, `organizations`, `applications`, `users`, `catalog`,
  `business_context`, `investigation_templates`, `investigations`,
  `remediation_templates`, `remediations`.
- Pydantic v2 models for every documented request and response shape,
  with snake↔camel aliasing and `extra='allow'` for forward-compat.
- Typed exception hierarchy mapped to HTTP status codes:
  `CommandZeroError` → `BadRequestError`, `UnauthorizedError`,
  `ForbiddenError`, `NotFoundError`, `ConflictError`,
  `UnprocessableEntityError`, `RateLimitError`, `ServerError`,
  `TransportError`. Every exception carries `trace_id`, `body`, `type`.
- `httpx`-based transport with bearer auth, automatic 429 retry with
  exponential backoff (honors `Retry-After`), and `X-Cmdzero-Traceid`
  capture on success and failure.
- `PaginatedIterator` lazy iterator over `next`-cursor list endpoints.
  Defaults to `GET` (broadest role compatibility); opt-in to `QUERY`
  with `method='QUERY'` for filters that exceed safe URL length.
- Closed-enum constants (`Severity`, `Sensitivity`, `ConfidenceLevel`,
  `Impact`, `InvestigationType`, `AlertEntryAction`, `AttributionType`,
  `BusinessContextStatus`, `PostbackMethod`, `HealthStatus`,
  `CreateInvestigationAction`).
- Open-enum constants (`InvestigationStatus`, `RemediationStatus`,
  `Role`) — typed as `str` on response models so the SDK accepts new
  server values without breaking.
- Convenience methods: `cz.users.assignable()`,
  `cz.catalog.alert_types()`,
  `cz.remediation_templates.for_subject_type(...)`.
- `cz.investigations.create_from_alert(...)` and
  `cz.investigations.create_from_template(...)` for the two main
  investigation creation flows.
- Auto-discovery of API key + org id from environment variables
  `COMMAND_ZERO_API` / `COMMAND_ZERO_ORG` (with
  `CMDZERO_API_KEY` / `CMDZERO_ORG_ID` as fallbacks).
- 49-check mocked-HTTP smoke test plus a live-API integration script.

### Known constraints

- The `severity`, `sensitivity`, `confidence_level`, `impact`, and
  `type` fields on `Investigation` and related response models are
  typed as `str` even though the spec describes them as closed enums —
  the production API returns mixed-case values (e.g. `'Low'` alongside
  `'high'`), so strict enum validation would reject real payloads.
- `cz.investigations.list(filter="createdBy/name eq …")` and other
  `createdBy/*` paths are documented in the spec's filter-syntax
  examples but rejected by `/investigations` with
  `400 — unknown filter field`. Filter by tag instead.
- The `MICROSOFT_ENTRA_USER` catalog type referenced in some external
  docs does not exist; the actual ID is
  `MICROSOFT_ENTRA_USER_PRINCIPAL_NAME`.

[Unreleased]: https://example.com/cmdzero-sdk/compare/0.1.0...HEAD
[0.1.0]: https://example.com/cmdzero-sdk/releases/tag/0.1.0
