# SDK Test Suite & Live Script Runner — Design

**Date:** 2026-04-28
**Status:** Approved (pending spec review)
**Owner:** eric@cmdzero.io
**Branch:** `sdk-tests-and-live-runner`

## Problem

The Python SDK at `sdk/cmdzero/` declares `pytest`, `pytest-httpx`, and `respx` as dev dependencies but ships **no tests**. Recent endpoint-path bugs in `sdk/cmdzero/resources/investigation_templates.py` and `remediation_templates.py` (called `/investigations/templates` instead of `/organizations/{org}/investigation-templates`) shipped silently because nothing verifies URL construction. The recipe scripts at the repo root have similarly never been run end-to-end against the live tenant in a structured, reportable way.

## Goal

1. Build a comprehensive `pytest`-based test suite for the SDK that asserts every public method calls the correct endpoint, with the correct HTTP method, request body, and response parsing.
2. Build a single-command harness (`run_all_scripts.py`) that runs every recipe script with every CLI flag against the live `warniCo` tenant and produces a structured report.

## Verified API context (from probes 2026-04-28)

- **Base URL:** `https://api.cmdzero.io/public/v1` (the recipes "public" API, distinct from Atlas)
- **Auth:** `Authorization: Bearer $CMDZERO_API_KEY` (NOT cookie-based; CLAUDE.md's cookie note is for Atlas)
- **Wrong path response:** HTTP 403 (not 404) — auth-shaped error obscures path errors at runtime
- **Trace header:** `X-Cmdzero-Traceid`
- **Tenant:** `warniCo`, org ID `51c264ff-5a98-4f15-b7e1-07158d35151c`, role `Investigators`
- **Path conventions:** URL segments use kebab-case (`/investigation-templates`, `/remediation-templates`); response body keys use camelCase (`investigationTemplates`, `remediationTemplates`)

The 403-on-wrong-path quirk is the reason the live-tenant approach can't substitute for mocked tests. We assert URL construction client-side via `respx`, which raises before any status code is involved.

## Architecture

### SDK test suite layout

```
sdk/
├── cmdzero/                       (existing — unchanged)
└── tests/                         (NEW)
    ├── __init__.py
    ├── conftest.py                — shared fixtures: mock client, response loader
    ├── fixtures/
    │   └── responses/             — JSON payloads captured from live API
    │       ├── health_ok.json
    │       ├── organizations_list.json
    │       ├── investigation_templates_list.json
    │       ├── investigation_templates_get.json
    │       ├── remediation_templates_list.json
    │       ├── investigations_list.json
    │       ├── investigations_create.json
    │       ├── remediations_list.json
    │       ├── applications_list.json
    │       ├── business_context_list.json
    │       ├── catalog_types_list.json
    │       ├── users_list.json
    │       ├── error_403.json
    │       ├── error_404.json
    │       ├── error_429.json
    │       └── pagination_page1.json / page2.json / page3_empty.json
    ├── test_health.py
    ├── test_organizations.py
    ├── test_applications.py
    ├── test_business_context.py
    ├── test_catalog.py
    ├── test_investigations.py
    ├── test_investigation_templates.py    (regression-anchored)
    ├── test_remediations.py
    ├── test_remediation_templates.py      (regression-anchored)
    ├── test_users.py
    └── test_pagination.py
```

### Mocking pattern

All tests use `respx.mock` to intercept `httpx` calls:

```python
@respx.mock
def test_investigation_templates_list_uses_correct_path(client, fixture):
    org = "51c264ff-5a98-4f15-b7e1-07158d35151c"
    route = respx.get(
        f"https://api.cmdzero.io/public/v1/organizations/{org}/investigation-templates"
    ).mock(return_value=httpx.Response(200, json=fixture("investigation_templates_list")))

    list(client.investigation_templates.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org}/investigation-templates"
```

Any unmocked HTTP call raises `respx.MockError`, so a path drift instantly fails the test.

### Shared `client` fixture

```python
@pytest.fixture
def client():
    return CmdzeroClient(
        api_key="test-key",
        base_url="https://api.cmdzero.io/public/v1",
        default_organization_id="51c264ff-5a98-4f15-b7e1-07158d35151c",
    )
```

Tests use this same configuration as production scripts to exercise identical path-construction logic.

## Test contract

Every public method on every resource gets at least one test that asserts **four things**:

1. **HTTP method** — `GET` / `POST` / `PUT` / `DELETE` / `QUERY`
2. **Exact URL** — including base, org segment, resource segment, IDs, query params
3. **Request body** (POST/PUT/PATCH/QUERY) — JSON shape matches the model dump
4. **Response parsing** — returned Pydantic model has expected fields populated from the fixture

### Anchor regressions explicitly

For the recently-fixed paths, name the regression in the test:

```python
def test_investigation_templates_uses_kebab_case_not_nested():
    """Regression: SDK previously called /investigations/templates (returns 403,
    looks like auth issue). Verifies the correct path
    /organizations/{org}/investigation-templates is constructed."""
```

Required regression tests:

- `test_investigation_templates.py::test_path_is_kebab_case_not_nested`
- `test_investigation_templates.py::test_path_is_kebab_case_not_camel_case`
- `test_remediation_templates.py::test_path_is_kebab_case_not_nested`
- `test_remediation_templates.py::test_path_is_kebab_case_not_camel_case`

### Pagination tests (`test_pagination.py`)

- Single-page response (no cursor) terminates immediately
- Multi-page traversal follows the `next` cursor across three pages
- Empty `next: ""` terminates the iterator
- `GET` and `QUERY` methods both work
- `limit` parameter is forwarded
- `filter` parameter is forwarded

### Error-handling tests

One per HTTP error class, asserting the SDK raises the right exception from `sdk/cmdzero/exceptions.py`:

- 401 → `AuthError` (or whatever the SDK names it)
- 403 → `PermissionError`-equivalent
- 404 → `NotFoundError`-equivalent
- 429 → retry then raise after budget exceeded
- 500 → `ServerError`-equivalent

### Fixture realism

Response payloads are captured from real API probes (e.g., the `investigationTemplates` body already pulled during design) and saved as JSON in `tests/fixtures/responses/`. Loaded by `conftest.py` via a `fixture(name)` helper. This catches model-mismatch bugs (new required field, renamed field, type drift) the moment the API changes.

## Live script execution plan

A new `run_all_scripts.py` at the repo root drives every recipe script, captures stdout/stderr/exit code, and writes structured reports.

### Execution order (least → most side-effecting)

| Order | Script | Side effects | Flags exercised |
|---|---|---|---|
| 1 | `health_check.py` | none | `--help`, default run |
| 2 | `cmdzero_client.py` | none (library) | `--help` only |
| 3 | `business_context.py` | none (read) | `--help`, `--list` |
| 4 | `investigation_pipeline_report.py` | none (read) | `--help`, default, `--days N` |
| 5 | `mssp_multi_tenant.py` | none (read across orgs) | `--help`, default |
| 6 | `sdk_live_test.py` | read (uses SDK) | `--help`, default |
| 7 | `template_investigation.py` | **creates investigation** | `--help`, `--list-templates`, `--template <id>` |
| 8 | `alert_investigation.py` | **creates investigation** | `--help`, full run |
| 9 | `automated_remediation.py` | **executes remediation** | `--help`, `--dry-run` (if exists), full run |
| 10 | `postback_receiver.py` | starts a Flask server | `--help` only — won't bind a port unattended |

### Flag discovery

Before running each script, the harness greps for `add_argument(...)` calls to enumerate every flag. Booleans get set; values get a sensible default; flags it can't safely value-fill get logged and skipped.

### Capture & report

For each `(script, flag-set)` row, the harness records:

- Command line invoked
- Exit code
- Wall-clock duration
- Last 50 lines of stdout
- Last 50 lines of stderr
- Any `X-Cmdzero-Traceid` values found in logs
- Any investigation IDs / remediation IDs created (extracted via regex from stdout)

Outputs:

- `script_run_report.json` — machine-readable
- `script_run_report.md` — human-readable summary table

### Abort condition

If steps 1–6 (read-only) all fail with auth errors, the harness aborts before running steps 7–10 (mutating). No point creating investigations if reads are broken.

### Sequencing with tests

Tests run **before** live scripts:

```
pytest sdk/tests/ → if green → python run_all_scripts.py
```

If mocked SDK tests fail, scripts may have stale assumptions and the live phase is skipped.

### Cleanup

Created investigation IDs and remediation IDs are logged but **not auto-deleted**. Cleanup is manual via the SOC dashboard. An opt-in `--cleanup` flag is a deferred follow-up.

## Success criteria

- `pytest sdk/tests/` runs in <10 seconds, exits 0, makes zero real network calls (`respx` blocks any unmocked request)
- Every public method on every SDK resource has at least one test
- All four regression tests for the recent endpoint fixes pass
- `run_all_scripts.py` produces a complete report; every script runs with every discovered flag; exit code per row recorded
- Live read-only scripts (steps 1–6) succeed against `warniCo`
- Mutating scripts (steps 7–9) execute and the report lists created investigation/remediation IDs

## Out of scope (deferred)

- Auto-cleanup of created investigations/remediations
- CI integration / GitHub Actions workflow
- Tests for the Go MCP server (`cmdzero-public-api-mcp/`) — separate codebase
- Linting / type-check tooling beyond what already exists
- Refactoring the recipe scripts themselves
- A dedicated test target for the public CLI shape of each recipe script (only `--help` and a default run are tested per script)

## Risks & callouts

- The `warniCo` tenant will accumulate real test investigations and remediations from the run. Cleanup is manual via the SOC dashboard.
- `postback_receiver.py` is `--help` only — full execution would require a publicly-reachable URL the API can POST to.
- If the API contract changes (new required field, renamed key, type drift), fixture-based response-parsing tests will fail. That is the *intended* behavior — it signals the SDK or fixtures need updating.
- The CLAUDE.md note about `/investigationTemplates` (camelCase) being the correct path is **incorrect for the public API** — it applies to Atlas only. Updating CLAUDE.md is listed as an optional follow-up deliverable.

## Open questions for the implementation plan

- Exact name of each exception class in `sdk/cmdzero/exceptions.py` (the spec assumes `AuthError`, `PermissionError`-equivalent, etc.; the plan should pin actual names)
- Whether `automated_remediation.py` has a real `--dry-run` flag or that needs to be inferred from `--help` output
- Whether `template_investigation.py`'s `--list-templates` flag exists today or only `--help` + a default `--template <id>` invocation is supported
