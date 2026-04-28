# SDK Test Suite & Live Script Runner Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a `respx`-mocked `pytest` suite for every public method on every Command Zero SDK resource (with named regression tests for the recent endpoint-path fixes), plus a `run_all_scripts.py` harness that executes every recipe script with every CLI flag against the live `warniCo` tenant and produces a structured report.

**Architecture:** Tests live under `sdk/tests/`, use `respx` to intercept `httpx` calls so URL construction is asserted directly. Real API response payloads are captured into `sdk/tests/fixtures/responses/` so model-parsing tests catch contract drift. The runner sits at the repo root, discovers each script's `argparse` shape (including subcommands), runs every `(script, subcommand, flag-set)` triple, captures stdout/stderr/exit code/duration/trace IDs/created-resource IDs, and writes JSON + Markdown reports.

**Tech Stack:** Python 3.10+, `pytest`, `respx`, `httpx`, `pydantic` v2 (already SDK deps); subprocess for the runner.

**Key facts established during design:**
- Top-level SDK client class is **`CommandZero`** (`from cmdzero import CommandZero`)
- Resource attributes: `cz.health`, `cz.organizations`, `cz.applications`, `cz.users`, `cz.catalog`, `cz.business_context`, `cz.investigation_templates`, `cz.investigations`, `cz.remediation_templates`, `cz.remediations`
- Exception classes: `CommandZeroError` (base), `TransportError`, `BadRequestError` (400), `UnauthorizedError` (401), `ForbiddenError` (403), `NotFoundError` (404), `ConflictError` (409), `UnprocessableEntityError` (422), `RateLimitError` (429), `ServerError` (5xx)
- Base URL: `https://api.cmdzero.io/public/v1`; auth: `Authorization: Bearer ${CMDZERO_API_KEY}`
- Test org id: `51c264ff-5a98-4f15-b7e1-07158d35151c` (`warniCo`)
- URL paths use kebab-case (`/investigation-templates`); response keys use camelCase (`investigationTemplates`)

**Branch:** `sdk-tests-and-live-runner` (already created)

---

## Phase 1 — Test infrastructure

### Task 1: Create tests directory, fixture-loader, and shared client fixture

**Files:**
- Create: `sdk/tests/__init__.py`
- Create: `sdk/tests/conftest.py`
- Create: `sdk/tests/fixtures/__init__.py`
- Create: `sdk/tests/fixtures/responses/.gitkeep`

- [ ] **Step 1: Create the empty package files**

```bash
mkdir -p sdk/tests/fixtures/responses
touch sdk/tests/__init__.py
touch sdk/tests/fixtures/__init__.py
touch sdk/tests/fixtures/responses/.gitkeep
```

- [ ] **Step 2: Write `sdk/tests/conftest.py`**

```python
"""Shared fixtures for the cmdzero SDK test suite.

All HTTP calls are intercepted by respx; no real network traffic is
ever issued from this suite.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cmdzero import CommandZero

BASE_URL = "https://api.cmdzero.io/public/v1"
ORG_ID = "51c264ff-5a98-4f15-b7e1-07158d35151c"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "responses"


@pytest.fixture
def org_id() -> str:
    return ORG_ID


@pytest.fixture
def base_url() -> str:
    return BASE_URL


@pytest.fixture
def client() -> CommandZero:
    """A CommandZero client wired to the canonical test base URL and
    org id. Pair every test with respx.mock to intercept the http calls."""
    return CommandZero(
        api_key="test-key",
        organization_id=ORG_ID,
        base_url=BASE_URL,
    )


@pytest.fixture
def fixture():
    """Load a JSON payload from sdk/tests/fixtures/responses/<name>.json."""
    def _load(name: str) -> dict:
        path = FIXTURES_DIR / f"{name}.json"
        return json.loads(path.read_text())
    return _load
```

- [ ] **Step 3: Verify pytest discovers the empty suite**

Run: `cd sdk && python -m pytest tests/ -v`
Expected: `no tests ran in <…>s` (zero collected, zero failures, exit code 5).

(Pytest exits 5 when no tests collected — that's fine for now; the dir is wired up.)

- [ ] **Step 4: Commit**

```bash
git add sdk/tests/
git commit -m "test(sdk): scaffold tests directory with shared fixtures

Adds conftest.py with reusable client and fixture-loader fixtures, plus
the fixtures/responses/ payload directory. No tests yet — establishing
the structure so subsequent tasks can drop test files in."
```

---

### Task 2: Capture real API response fixtures

Pull live response bodies for each resource into `sdk/tests/fixtures/responses/`. These payloads make response-parsing tests realistic and catch API contract drift.

**Files:**
- Create: `sdk/tests/fixtures/responses/health_ok.json`
- Create: `sdk/tests/fixtures/responses/organizations_list.json`
- Create: `sdk/tests/fixtures/responses/investigation_templates_list.json`
- Create: `sdk/tests/fixtures/responses/remediation_templates_list.json`
- Create: `sdk/tests/fixtures/responses/applications_list.json`
- Create: `sdk/tests/fixtures/responses/users_list.json`
- Create: `sdk/tests/fixtures/responses/catalog_types_list.json`
- Create: `sdk/tests/fixtures/responses/business_context_list.json`
- Create: `sdk/tests/fixtures/responses/investigations_list.json`
- Create: `sdk/tests/fixtures/responses/remediations_list.json`
- Create: `sdk/tests/fixtures/responses/error_403.json`
- Create: `sdk/tests/fixtures/responses/error_404.json`
- Create: `sdk/tests/fixtures/responses/error_429.json`

- [ ] **Step 1: Capture every list/health response from the live API**

```bash
ORG="51c264ff-5a98-4f15-b7e1-07158d35151c"
H="Authorization: Bearer $CMDZERO_API_KEY"
DIR=sdk/tests/fixtures/responses

curl -sS -H "$H" "https://api.cmdzero.io/public/v1/ok" > "$DIR/health_ok.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations?limit=5" > "$DIR/organizations_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/investigation-templates?limit=3" > "$DIR/investigation_templates_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/remediation-templates?limit=3" > "$DIR/remediation_templates_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/applications?limit=3" > "$DIR/applications_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/users?limit=3" > "$DIR/users_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/catalog/types?limit=3" > "$DIR/catalog_types_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/business-context/uploads?limit=3" > "$DIR/business_context_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/investigations?limit=3" > "$DIR/investigations_list.json"
curl -sS -H "$H" "https://api.cmdzero.io/public/v1/organizations/$ORG/remediations?limit=3" > "$DIR/remediations_list.json"
```

- [ ] **Step 2: Verify each file is non-empty valid JSON**

Run:
```bash
for f in sdk/tests/fixtures/responses/*.json; do
  python -c "import json,sys; json.load(open('$f')); print('$f OK')"
done
```
Expected: every line ends with `OK`.

- [ ] **Step 3: Hand-author the three error fixtures**

These are realistic Command Zero error envelopes. Save each file:

`sdk/tests/fixtures/responses/error_403.json`:
```json
{"message":"forbidden","type":"permission_denied"}
```

`sdk/tests/fixtures/responses/error_404.json`:
```json
{"message":"not found","type":"not_found"}
```

`sdk/tests/fixtures/responses/error_429.json`:
```json
{"message":"rate limited","type":"rate_limit_exceeded"}
```

- [ ] **Step 4: Sanity-check fixture shape**

Run:
```bash
python -c "import json; d=json.load(open('sdk/tests/fixtures/responses/investigation_templates_list.json')); assert 'investigationTemplates' in d, list(d); print('shape OK')"
```
Expected: `shape OK`

- [ ] **Step 5: Commit**

```bash
git add sdk/tests/fixtures/responses/
git commit -m "test(sdk): capture live API response payloads as fixtures

Real-data fixtures for every list endpoint plus error variants. Used by
the upcoming respx-mocked test suite so response-parsing tests catch
contract drift the moment the API changes."
```

---

## Phase 2 — Per-resource SDK tests

Each resource test follows the same pattern: respx-mock the expected URL, call the SDK method, assert the route was called with the exact path/method/body, and assert the parsed response model has expected fields.

### Task 3: `test_health.py`

**Files:**
- Create: `sdk/tests/test_health.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_health.py`:
```python
"""Health resource: cz.health.check() should hit /ok unauthenticated-style."""
from __future__ import annotations

import httpx
import respx

from cmdzero import HealthResponse


@respx.mock
def test_health_check_calls_ok_endpoint(client, fixture, base_url):
    route = respx.get(f"{base_url}/ok").mock(
        return_value=httpx.Response(200, json=fixture("health_ok"))
    )

    result = client.health.check()

    assert route.called
    assert route.calls[0].request.method == "GET"
    assert route.calls[0].request.url.path == "/public/v1/ok"
    assert isinstance(result, HealthResponse)
    assert result.status == "ok"
```

- [ ] **Step 2: Run the test**

Run: `cd sdk && python -m pytest tests/test_health.py -v`
Expected: 1 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_health.py
git commit -m "test(sdk): cover health.check() endpoint"
```

---

### Task 4: `test_organizations.py`

**Files:**
- Create: `sdk/tests/test_organizations.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_organizations.py`:
```python
"""Organizations resource: cz.organizations.list() iterates /organizations."""
from __future__ import annotations

import httpx
import respx

from cmdzero import Organization


@respx.mock
def test_organizations_list_calls_top_level_organizations(client, fixture, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json=fixture("organizations_list"))
    )

    orgs = list(client.organizations.list())

    assert route.called
    assert route.calls[0].request.url.path == "/public/v1/organizations"
    assert all(isinstance(o, Organization) for o in orgs)
    assert any(o.id == "51c264ff-5a98-4f15-b7e1-07158d35151c" for o in orgs)


@respx.mock
def test_organizations_list_forwards_filter_and_limit(client, fixture, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json=fixture("organizations_list"))
    )

    list(client.organizations.list(filter="role eq 'Investigators'", limit=10))

    assert route.called
    sent = route.calls[0].request.url
    assert sent.params.get("filter") == "role eq 'Investigators'"
    assert sent.params.get("limit") == "10"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_organizations.py -v`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_organizations.py
git commit -m "test(sdk): cover organizations.list() with filter/limit forwarding"
```

---

### Task 5: `test_applications.py`

**Files:**
- Create: `sdk/tests/test_applications.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_applications.py`:
```python
"""Applications resource: list and get."""
from __future__ import annotations

import httpx
import respx

from cmdzero import Application


@respx.mock
def test_applications_list_uses_org_scoped_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/applications").mock(
        return_value=httpx.Response(200, json=fixture("applications_list"))
    )

    apps = list(client.applications.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/applications"
    assert all(isinstance(a, Application) for a in apps)


@respx.mock
def test_applications_get_appends_id_to_path(client, fixture, base_url, org_id):
    sample = fixture("applications_list")["applications"][0]
    app_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/applications/{app_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    app = client.applications.get(app_id)

    assert route.called
    assert isinstance(app, Application)
    assert app.id == app_id
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_applications.py -v`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_applications.py
git commit -m "test(sdk): cover applications.list() and applications.get()"
```

---

### Task 6: `test_users.py`

**Files:**
- Create: `sdk/tests/test_users.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_users.py`:
```python
"""Users resource: list, get, assignable."""
from __future__ import annotations

import httpx
import respx

from cmdzero import User


@respx.mock
def test_users_list_uses_org_scoped_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/users").mock(
        return_value=httpx.Response(200, json=fixture("users_list"))
    )

    users = list(client.users.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/users"
    assert all(isinstance(u, User) for u in users)


@respx.mock
def test_users_get_appends_user_id(client, fixture, base_url, org_id):
    sample = fixture("users_list")["users"][0]
    user_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/users/{user_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    user = client.users.get(user_id)

    assert route.called
    assert user.id == user_id


@respx.mock
def test_users_assignable_uses_assignable_subpath(client, fixture, base_url, org_id):
    route = respx.get(
        f"{base_url}/organizations/{org_id}/users/assignable"
    ).mock(return_value=httpx.Response(200, json=fixture("users_list")))

    list(client.users.assignable())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/users/assignable"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_users.py -v`
Expected: 3 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_users.py
git commit -m "test(sdk): cover users.list/get/assignable"
```

---

### Task 7: `test_catalog.py`

**Files:**
- Create: `sdk/tests/test_catalog.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_catalog.py`:
```python
"""Catalog resource: types list, alert_types convenience, get."""
from __future__ import annotations

import httpx
import respx

from cmdzero import CatalogType


@respx.mock
def test_catalog_list_uses_catalog_types_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/catalog/types").mock(
        return_value=httpx.Response(200, json=fixture("catalog_types_list"))
    )

    types = list(client.catalog.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/catalog/types"
    assert all(isinstance(t, CatalogType) for t in types)


@respx.mock
def test_catalog_alert_types_filters_by_alert_kind(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/catalog/types").mock(
        return_value=httpx.Response(200, json=fixture("catalog_types_list"))
    )

    list(client.catalog.alert_types())

    assert route.called
    sent = route.calls[0].request.url
    assert "filter" in sent.params, f"expected filter param, got {dict(sent.params)}"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_catalog.py -v`
Expected: 2 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_catalog.py
git commit -m "test(sdk): cover catalog.list() and catalog.alert_types()"
```

---

### Task 8: `test_business_context.py`

**Files:**
- Create: `sdk/tests/test_business_context.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_business_context.py`:
```python
"""Business context resource: list, get, upload, replace, delete."""
from __future__ import annotations

import httpx
import respx

from cmdzero import (
    BusinessContextUpload,
    CreateBusinessContextUploadRequest,
    ReplaceBusinessContextUploadRequest,
)


BC_PATH = "business-context/uploads"


@respx.mock
def test_business_context_list_uses_kebab_uploads_path(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/{BC_PATH}").mock(
        return_value=httpx.Response(200, json=fixture("business_context_list"))
    )

    list(client.business_context.list())

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{BC_PATH}"


@respx.mock
def test_business_context_get_appends_id(client, fixture, base_url, org_id):
    sample = fixture("business_context_list")["uploads"][0] if fixture("business_context_list").get("uploads") else None
    if not sample:
        # Empty live fixture is fine — synthesise a minimal one.
        sample = {"id": "abc-123", "name": "x", "status": "ready"}
    upload_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/{BC_PATH}/{upload_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    upload = client.business_context.get(upload_id)

    assert route.called
    assert isinstance(upload, BusinessContextUpload)


@respx.mock
def test_business_context_upload_posts_to_collection(client, base_url, org_id):
    route = respx.post(f"{base_url}/organizations/{org_id}/{BC_PATH}").mock(
        return_value=httpx.Response(
            200,
            json={"id": "new-upload-id", "name": "HR Directory", "status": "ready"},
        )
    )

    body = CreateBusinessContextUploadRequest(name="HR Directory", description="x", contents="data")
    result = client.business_context.upload(body)

    assert route.called
    assert route.calls[0].request.method == "POST"
    assert isinstance(result, BusinessContextUpload)


@respx.mock
def test_business_context_replace_puts_to_id(client, base_url, org_id):
    upload_id = "abc-123"
    route = respx.put(
        f"{base_url}/organizations/{org_id}/{BC_PATH}/{upload_id}"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"id": upload_id, "name": "HR Directory", "status": "ready"},
        )
    )

    body = ReplaceBusinessContextUploadRequest(name="HR Directory", description="x", contents="data")
    result = client.business_context.replace(upload_id, body)

    assert route.called
    assert route.calls[0].request.method == "PUT"
    assert isinstance(result, BusinessContextUpload)


@respx.mock
def test_business_context_delete_calls_delete_on_id(client, base_url, org_id):
    upload_id = "abc-123"
    route = respx.delete(
        f"{base_url}/organizations/{org_id}/{BC_PATH}/{upload_id}"
    ).mock(return_value=httpx.Response(204))

    client.business_context.delete(upload_id)

    assert route.called
    assert route.calls[0].request.method == "DELETE"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_business_context.py -v`
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_business_context.py
git commit -m "test(sdk): cover business_context list/get/upload/replace/delete"
```

---

### Task 9: `test_investigation_templates.py` (regression-anchored)

**Files:**
- Create: `sdk/tests/test_investigation_templates.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_investigation_templates.py`:
```python
"""Investigation templates resource: list and get.

Includes named regression tests for the recently-fixed endpoint path
bug. Prior to the fix, the SDK called /investigations/templates which
returned 403 (looking like an auth issue). The correct path is
/organizations/{org}/investigation-templates.
"""
from __future__ import annotations

import httpx
import respx

from cmdzero import InvestigationTemplate

CORRECT_PATH = "investigation-templates"
WRONG_NESTED = "investigations/templates"
WRONG_CAMEL = "investigationTemplates"


@respx.mock
def test_investigation_templates_list(client, fixture, base_url, org_id):
    route = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}"
    ).mock(return_value=httpx.Response(200, json=fixture("investigation_templates_list")))

    templates = list(client.investigation_templates.list())

    assert route.called
    assert all(isinstance(t, InvestigationTemplate) for t in templates)


@respx.mock
def test_investigation_templates_get_appends_id(client, fixture, base_url, org_id):
    sample = fixture("investigation_templates_list")["investigationTemplates"][0]
    template_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}/{template_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    template = client.investigation_templates.get(template_id)

    assert route.called
    assert template.id == template_id


@respx.mock
def test_path_is_kebab_case_not_nested(client, fixture, base_url, org_id):
    """REGRESSION: previously called /investigations/templates which 403s."""
    correct = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}"
    ).mock(return_value=httpx.Response(200, json=fixture("investigation_templates_list")))
    wrong = respx.get(f"{base_url}/organizations/{org_id}/{WRONG_NESTED}")

    list(client.investigation_templates.list())

    assert correct.called, "SDK must call /investigation-templates (the correct path)"
    assert not wrong.called, "SDK must NOT call /investigations/templates (the bug)"


@respx.mock
def test_path_is_kebab_case_not_camel_case(client, fixture, base_url, org_id):
    """REGRESSION: per CLAUDE.md the Atlas API uses camelCase, but the
    public API uses kebab-case. Confirm we use kebab."""
    correct = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}"
    ).mock(return_value=httpx.Response(200, json=fixture("investigation_templates_list")))
    wrong = respx.get(f"{base_url}/organizations/{org_id}/{WRONG_CAMEL}")

    list(client.investigation_templates.list())

    assert correct.called
    assert not wrong.called, "Public API path is kebab-case, not camelCase"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_investigation_templates.py -v`
Expected: 4 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_investigation_templates.py
git commit -m "test(sdk): cover investigation_templates with regression tests for path fix

Anchors the recent endpoint path fix with named regression tests so
the kebab-vs-camel and nested-vs-flat path bugs cannot recur silently."
```

---

### Task 10: `test_remediation_templates.py` (regression-anchored)

**Files:**
- Create: `sdk/tests/test_remediation_templates.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_remediation_templates.py`:
```python
"""Remediation templates resource: list, get, for_subject_type.

Includes named regression tests for the recently-fixed endpoint path
bug — see test_investigation_templates.py for the parallel fix.
"""
from __future__ import annotations

import httpx
import respx

from cmdzero import RemediationTemplate

CORRECT_PATH = "remediation-templates"
WRONG_NESTED = "remediations/templates"
WRONG_CAMEL = "remediationTemplates"


@respx.mock
def test_remediation_templates_list(client, fixture, base_url, org_id):
    route = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}"
    ).mock(return_value=httpx.Response(200, json=fixture("remediation_templates_list")))

    list(client.remediation_templates.list())
    assert route.called


@respx.mock
def test_remediation_templates_get(client, fixture, base_url, org_id):
    items = fixture("remediation_templates_list").get("remediationTemplates", [])
    sample = items[0] if items else {"id": "abc", "name": "x", "subjectType": "user"}
    template_id = sample["id"]
    route = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}/{template_id}"
    ).mock(return_value=httpx.Response(200, json=sample))

    result = client.remediation_templates.get(template_id)
    assert route.called
    assert isinstance(result, RemediationTemplate)


@respx.mock
def test_remediation_templates_for_subject_type_filters(client, fixture, base_url, org_id):
    route = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}"
    ).mock(return_value=httpx.Response(200, json=fixture("remediation_templates_list")))

    list(client.remediation_templates.for_subject_type("user"))
    assert route.called
    assert "filter" in route.calls[0].request.url.params


@respx.mock
def test_path_is_kebab_case_not_nested(client, fixture, base_url, org_id):
    """REGRESSION: previously called /remediations/templates."""
    correct = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}"
    ).mock(return_value=httpx.Response(200, json=fixture("remediation_templates_list")))
    wrong = respx.get(f"{base_url}/organizations/{org_id}/{WRONG_NESTED}")

    list(client.remediation_templates.list())
    assert correct.called
    assert not wrong.called


@respx.mock
def test_path_is_kebab_case_not_camel_case(client, fixture, base_url, org_id):
    """REGRESSION: confirm kebab not camel."""
    correct = respx.get(
        f"{base_url}/organizations/{org_id}/{CORRECT_PATH}"
    ).mock(return_value=httpx.Response(200, json=fixture("remediation_templates_list")))
    wrong = respx.get(f"{base_url}/organizations/{org_id}/{WRONG_CAMEL}")

    list(client.remediation_templates.list())
    assert correct.called
    assert not wrong.called
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_remediation_templates.py -v`
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_remediation_templates.py
git commit -m "test(sdk): cover remediation_templates with regression tests for path fix"
```

---

### Task 11: `test_investigations.py`

**Files:**
- Create: `sdk/tests/test_investigations.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_investigations.py`:
```python
"""Investigations resource: list, get, create, create_from_alert,
create_from_template, update."""
from __future__ import annotations

import httpx
import respx

from cmdzero import (
    CreateInvestigationRequest,
    Investigation,
    UpdateInvestigationRequest,
)

PATH = "investigations"


@respx.mock
def test_investigations_list(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=fixture("investigations_list"))
    )

    list(client.investigations.list())
    assert route.called


@respx.mock
def test_investigations_get(client, fixture, base_url, org_id):
    items = fixture("investigations_list").get("investigations", [])
    sample = items[0] if items else {"id": "abc-123", "title": "x", "status": "pending-review", "severity": "low"}
    inv_id = sample["id"]
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}/{inv_id}").mock(
        return_value=httpx.Response(200, json=sample)
    )

    inv = client.investigations.get(inv_id)
    assert route.called
    assert isinstance(inv, Investigation)


@respx.mock
def test_investigations_create_posts_to_collection(client, base_url, org_id):
    route = respx.post(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json={"id": "new-id", "status": "open"})
    )

    body = CreateInvestigationRequest(
        title="Test investigation",
        type="generic",
        severity="low",
    )
    client.investigations.create(body)

    assert route.called
    assert route.calls[0].request.method == "POST"


@respx.mock
def test_investigations_create_from_alert_uses_alerts_subpath(client, base_url, org_id):
    route = respx.post(
        f"{base_url}/organizations/{org_id}/{PATH}/alerts"
    ).mock(return_value=httpx.Response(200, json={"id": "from-alert"}))

    # Method signature: create_from_alert(alert_type=..., alert_data=..., ...)
    client.investigations.create_from_alert(
        alert_type="example.alert",
        alert_data={"key": "value"},
    )

    assert route.called
    assert route.calls[0].request.method == "POST"
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}/alerts"


@respx.mock
def test_investigations_create_from_template_uses_templates_subpath(client, base_url, org_id):
    template_id = "tmpl-abc"
    route = respx.post(
        f"{base_url}/organizations/{org_id}/{PATH}/templates/{template_id}"
    ).mock(return_value=httpx.Response(200, json={"id": "from-template"}))

    client.investigations.create_from_template(template_id, leads=[])

    assert route.called
    assert route.calls[0].request.url.path == \
        f"/public/v1/organizations/{org_id}/{PATH}/templates/{template_id}"


@respx.mock
def test_investigations_update_patches_id(client, base_url, org_id):
    inv_id = "abc-123"
    route = respx.patch(
        f"{base_url}/organizations/{org_id}/{PATH}/{inv_id}"
    ).mock(return_value=httpx.Response(200, json={"id": inv_id, "status": "completed"}))

    body = UpdateInvestigationRequest(status="completed")
    client.investigations.update(inv_id, body)

    assert route.called
    assert route.calls[0].request.method == "PATCH"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_investigations.py -v`
Expected: 6 passed. If any fail because of method-signature mismatches with the real SDK (e.g. `create_from_alert` parameter names), fix the test to match the actual signature in `sdk/cmdzero/resources/investigations.py` — do not change the SDK to match the test.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_investigations.py
git commit -m "test(sdk): cover investigations list/get/create/from_alert/from_template/update"
```

---

### Task 12: `test_remediations.py`

**Files:**
- Create: `sdk/tests/test_remediations.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_remediations.py`:
```python
"""Remediations resource: list, get, create."""
from __future__ import annotations

import httpx
import respx

from cmdzero import CreateRemediationRequest, Remediation

PATH = "remediations"


@respx.mock
def test_remediations_list(client, fixture, base_url, org_id):
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json=fixture("remediations_list"))
    )

    list(client.remediations.list())
    assert route.called


@respx.mock
def test_remediations_get(client, fixture, base_url, org_id):
    items = fixture("remediations_list").get("remediations", [])
    sample = items[0] if items else {"id": "abc-123", "status": "pending"}
    rem_id = sample["id"]
    route = respx.get(f"{base_url}/organizations/{org_id}/{PATH}/{rem_id}").mock(
        return_value=httpx.Response(200, json=sample)
    )

    rem = client.remediations.get(rem_id)
    assert route.called
    assert isinstance(rem, Remediation)


@respx.mock
def test_remediations_create_posts_to_collection(client, base_url, org_id):
    route = respx.post(f"{base_url}/organizations/{org_id}/{PATH}").mock(
        return_value=httpx.Response(200, json={"id": "new-rem-id", "status": "pending"})
    )

    body = CreateRemediationRequest(
        templateId="tmpl-abc",
        investigationId="inv-abc",
        justification="auto",
    )
    client.remediations.create(body)

    assert route.called
    assert route.calls[0].request.method == "POST"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_remediations.py -v`
Expected: 3 passed. If `CreateRemediationRequest` field names differ, adjust the test body to match the real model in `sdk/cmdzero/models.py`.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_remediations.py
git commit -m "test(sdk): cover remediations list/get/create"
```

---

## Phase 3 — Cross-cutting tests

### Task 13: `test_pagination.py`

**Files:**
- Create: `sdk/tests/test_pagination.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_pagination.py`:
```python
"""Cross-cutting pagination behavior. Uses organizations.list() as the
exercise vehicle but the logic under test is in
sdk/cmdzero/pagination.py and sdk/cmdzero/resources/base.py."""
from __future__ import annotations

import httpx
import respx


@respx.mock
def test_single_page_terminates_when_next_is_empty(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [{"id": "a"}], "next": ""})
    )

    orgs = list(client.organizations.list())
    assert len(orgs) == 1


@respx.mock
def test_multi_page_follows_next_cursor(client, base_url):
    page1 = {"organizations": [{"id": "a"}], "next": "cursor-1"}
    page2 = {"organizations": [{"id": "b"}], "next": "cursor-2"}
    page3 = {"organizations": [{"id": "c"}], "next": ""}

    route = respx.get(f"{base_url}/organizations").mock(
        side_effect=[
            httpx.Response(200, json=page1),
            httpx.Response(200, json=page2),
            httpx.Response(200, json=page3),
        ]
    )

    orgs = list(client.organizations.list())

    assert [o.id for o in orgs] == ["a", "b", "c"]
    assert route.call_count == 3
    # second call must include the cursor returned by the first
    assert route.calls[1].request.url.params.get("next") == "cursor-1"
    assert route.calls[2].request.url.params.get("next") == "cursor-2"


@respx.mock
def test_empty_first_page_returns_no_items(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [], "next": ""})
    )

    assert list(client.organizations.list()) == []


@respx.mock
def test_limit_is_forwarded(client, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [], "next": ""})
    )

    list(client.organizations.list(limit=25))

    assert route.calls[0].request.url.params.get("limit") == "25"


@respx.mock
def test_filter_is_forwarded(client, base_url):
    route = respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [], "next": ""})
    )

    list(client.organizations.list(filter="role eq 'Investigators'"))

    assert route.calls[0].request.url.params.get("filter") == "role eq 'Investigators'"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_pagination.py -v`
Expected: 5 passed.

- [ ] **Step 3: Commit**

```bash
git add sdk/tests/test_pagination.py
git commit -m "test(sdk): cover pagination cursor traversal and param forwarding"
```

---

### Task 14: `test_errors.py`

**Files:**
- Create: `sdk/tests/test_errors.py`

- [ ] **Step 1: Write the test file**

`sdk/tests/test_errors.py`:
```python
"""Cross-cutting error handling. Each HTTP error class maps to a
specific exception subclass in cmdzero.exceptions."""
from __future__ import annotations

import httpx
import pytest
import respx

from cmdzero import (
    BadRequestError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    ServerError,
    UnauthorizedError,
    UnprocessableEntityError,
)


@respx.mock
def test_400_raises_bad_request(client, fixture, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(400, json={"message": "bad request", "type": "bad_request"})
    )
    with pytest.raises(BadRequestError) as exc:
        list(client.organizations.list())
    assert exc.value.status == 400


@respx.mock
def test_401_raises_unauthorized(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(401, json={"message": "unauthorized"})
    )
    with pytest.raises(UnauthorizedError):
        list(client.organizations.list())


@respx.mock
def test_403_raises_forbidden(client, fixture, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(403, json=fixture("error_403"))
    )
    with pytest.raises(ForbiddenError):
        list(client.organizations.list())


@respx.mock
def test_404_raises_not_found(client, fixture, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(404, json=fixture("error_404"))
    )
    with pytest.raises(NotFoundError):
        list(client.organizations.list())


@respx.mock
def test_409_raises_conflict(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(409, json={"message": "conflict"})
    )
    with pytest.raises(ConflictError):
        list(client.organizations.list())


@respx.mock
def test_422_raises_unprocessable(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(422, json={"message": "invalid"})
    )
    with pytest.raises(UnprocessableEntityError):
        list(client.organizations.list())


@respx.mock
def test_429_after_retry_budget_raises_rate_limit(client, fixture, base_url):
    """The transport retries 429 up to max_retries; once exhausted it raises."""
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(
            429,
            json=fixture("error_429"),
            headers={"Retry-After": "0"},
        )
    )
    with pytest.raises(RateLimitError):
        list(client.organizations.list())


@respx.mock
def test_500_raises_server_error(client, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(500, json={"message": "boom"})
    )
    with pytest.raises(ServerError):
        list(client.organizations.list())


@respx.mock
def test_trace_id_propagated_on_error(client, fixture, base_url):
    respx.get(f"{base_url}/organizations").mock(
        return_value=httpx.Response(
            403,
            json=fixture("error_403"),
            headers={"X-Cmdzero-Traceid": "trace-abc-123"},
        )
    )
    with pytest.raises(ForbiddenError) as exc:
        list(client.organizations.list())
    assert exc.value.trace_id == "trace-abc-123"
```

- [ ] **Step 2: Run**

Run: `cd sdk && python -m pytest tests/test_errors.py -v`
Expected: 9 passed. The 429 test may need patience — the transport retries with backoff. If runtime is excessive, adjust the client fixture's `max_retries` or add `Retry-After: 0` headers (already done in the test).

- [ ] **Step 3: Run the full SDK suite to confirm everything still passes together**

Run: `cd sdk && python -m pytest tests/ -v`
Expected: all tests across all files pass; runtime well under 10 seconds.

- [ ] **Step 4: Commit**

```bash
git add sdk/tests/test_errors.py
git commit -m "test(sdk): cover http error → exception class mapping and trace_id propagation"
```

---

## Phase 4 — Live script runner

### Task 15: Skeleton runner — `--help` for every script

**Files:**
- Create: `run_all_scripts.py`

- [ ] **Step 1: Write the skeleton runner**

`run_all_scripts.py`:
```python
"""Run every recipe script with every CLI flag combination, capture
stdout/stderr/exit code/duration/trace IDs/created-resource IDs, and
write structured reports to script_run_report.json and
script_run_report.md.

This is a destructive harness: scripts in the "mutating" group create
real investigations and remediations on the configured warniCo tenant.
The harness aborts before the mutating phase if any read-only script
fails with an auth error.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
REPORT_JSON = REPO_ROOT / "script_run_report.json"
REPORT_MD = REPO_ROOT / "script_run_report.md"

# Order matters: read-only first, mutating last. The harness aborts
# before mutating if any read-only run fails with an auth error.
READ_ONLY_SCRIPTS = [
    "health_check.py",
    "cmdzero_client.py",
    "business_context.py",
    "investigation_pipeline_report.py",
    "mssp_multi_tenant.py",
    "sdk_live_test.py",
]
MUTATING_SCRIPTS = [
    "template_investigation.py",
    "alert_investigation.py",
    "automated_remediation.py",
    "postback_receiver.py",  # --help only — won't bind a port
]
ALL_SCRIPTS = READ_ONLY_SCRIPTS + MUTATING_SCRIPTS


@dataclass
class RunResult:
    script: str
    args: list[str]
    exit_code: int
    duration_s: float
    stdout_tail: str
    stderr_tail: str
    trace_ids: list[str] = field(default_factory=list)
    created_investigation_ids: list[str] = field(default_factory=list)
    created_remediation_ids: list[str] = field(default_factory=list)


def run_one(script: str, args: list[str], timeout: int = 60) -> RunResult:
    """Run `python <script> <args>` from the repo root, capture output."""
    cmd = [sys.executable, script, *args]
    start = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as e:
        exit_code = -1
        stdout = (e.stdout or b"").decode("utf-8", errors="replace")
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") + f"\n[timeout after {timeout}s]"
    duration = time.time() - start

    trace_ids = sorted(set(re.findall(r"[a-f0-9]{32}", stdout + "\n" + stderr)))
    inv_ids = sorted(set(re.findall(r"\binvestigation[_ -]?id[:= ]+([0-9a-f-]{36})", stdout, re.I)))
    rem_ids = sorted(set(re.findall(r"\bremediation[_ -]?id[:= ]+([0-9a-f-]{36})", stdout, re.I)))

    return RunResult(
        script=script,
        args=args,
        exit_code=exit_code,
        duration_s=round(duration, 3),
        stdout_tail="\n".join(stdout.splitlines()[-50:]),
        stderr_tail="\n".join(stderr.splitlines()[-50:]),
        trace_ids=trace_ids,
        created_investigation_ids=inv_ids,
        created_remediation_ids=rem_ids,
    )


def write_reports(results: list[RunResult]) -> None:
    REPORT_JSON.write_text(json.dumps([asdict(r) for r in results], indent=2))

    lines = ["# Live script run report\n"]
    lines.append(f"Total runs: {len(results)}\n")
    passed = sum(1 for r in results if r.exit_code == 0)
    lines.append(f"Passed: {passed} / {len(results)}\n\n")
    lines.append("| Script | Args | Exit | Duration | Created |\n")
    lines.append("|---|---|---|---|---|\n")
    for r in results:
        created = []
        if r.created_investigation_ids:
            created.append(f"inv: {len(r.created_investigation_ids)}")
        if r.created_remediation_ids:
            created.append(f"rem: {len(r.created_remediation_ids)}")
        lines.append(
            f"| {r.script} | `{' '.join(r.args) or '(none)'}` | {r.exit_code} | "
            f"{r.duration_s}s | {', '.join(created) or '-'} |\n"
        )
    REPORT_MD.write_text("".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("help", "read", "mutate", "all"),
        default="help",
        help="Which phase to run. 'help' runs --help for every script (safe smoke).",
    )
    args = parser.parse_args()

    results: list[RunResult] = []

    # Phase: --help
    if args.phase in ("help", "all"):
        for script in ALL_SCRIPTS:
            results.append(run_one(script, ["--help"], timeout=15))

    write_reports(results)
    print(f"Wrote {REPORT_JSON} and {REPORT_MD}")
    return 0 if all(r.exit_code == 0 for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run --help phase**

Run: `python run_all_scripts.py --phase help`
Expected: writes `script_run_report.json` and `script_run_report.md`, every script's `--help` exits 0. If any script fails to print help, fix the script (or the script-runner if the failure is a runner bug) before continuing.

- [ ] **Step 3: Inspect the markdown report**

Run: `cat script_run_report.md`
Expected: 10 rows, all exit 0, durations < a few seconds each.

- [ ] **Step 4: Commit**

```bash
git add run_all_scripts.py script_run_report.json script_run_report.md
git commit -m "feat: add live-script runner with --help smoke phase

Phase 1 of the runner: invokes --help on every recipe script and writes
script_run_report.{json,md}. Subsequent tasks add read-only and
mutating phases."
```

---

### Task 16: Read-only phase — exercise non-mutating subcommands and flags

**Files:**
- Modify: `run_all_scripts.py`

- [ ] **Step 1: Add the read-only invocation table at module scope**

Insert after the `ALL_SCRIPTS` block in `run_all_scripts.py`:

```python
# Each entry: (script, args). One entry per discoverable read-only invocation.
# Subcommands (where present) are exercised explicitly here rather than auto-
# discovered, because each subcommand has different required arguments.
READ_ONLY_INVOCATIONS: list[tuple[str, list[str]]] = [
    ("health_check.py", []),
    ("business_context.py", ["list"]),
    ("investigation_pipeline_report.py", ["pending-review"]),
    ("investigation_pipeline_report.py", ["pending-review", "--severity", "high"]),
    ("investigation_pipeline_report.py", ["sla"]),
    ("mssp_multi_tenant.py", []),
    ("sdk_live_test.py", []),
    # automated_remediation has a read-only `templates` subcommand
    ("automated_remediation.py", ["templates"]),
    ("automated_remediation.py", ["templates", "--subject-type", "user"]),
]
```

- [ ] **Step 2: Wire the read-only phase into `main()`**

Replace the `# Phase: --help` block in `main()` with:

```python
    # Phase: --help
    if args.phase in ("help", "read", "mutate", "all"):
        for script in ALL_SCRIPTS:
            results.append(run_one(script, ["--help"], timeout=15))

    # Phase: read-only
    if args.phase in ("read", "mutate", "all"):
        # Abort guard: if every --help passed but auth is broken, the
        # read-only phase will reveal it. We still attempt the read phase
        # before mutating; mutate phase has its own abort below.
        for script, run_args in READ_ONLY_INVOCATIONS:
            results.append(run_one(script, run_args, timeout=60))
```

- [ ] **Step 3: Run the read phase**

Run: `python run_all_scripts.py --phase read`
Expected: every read-only invocation exits 0. Trace IDs appear in the JSON report. No created-resource IDs (read-only).

- [ ] **Step 4: Inspect any failures**

If any row has `exit_code != 0`, open the JSON report and read the `stderr_tail` for that row. Common causes: missing `CMDZERO_API_KEY`, missing org access, transient API issue. Fix the underlying issue and re-run before continuing.

- [ ] **Step 5: Commit**

```bash
git add run_all_scripts.py script_run_report.json script_run_report.md
git commit -m "feat(runner): add read-only phase exercising every non-mutating subcommand"
```

---

### Task 17: Mutating phase — with abort condition

**Files:**
- Modify: `run_all_scripts.py`

- [ ] **Step 1: Add the mutating invocation table at module scope**

Insert after `READ_ONLY_INVOCATIONS`:

```python
# Mutating: each invocation can create real investigations or remediations.
# template_investigation.py --list lists templates without creating; the
# create branch needs a template id which must be supplied via env var
# CMDZERO_TEST_TEMPLATE_ID and a lead via CMDZERO_TEST_LEAD if specified.
MUTATING_INVOCATIONS: list[tuple[str, list[str]]] = [
    ("template_investigation.py", ["--list"]),
    # Real create — only if the env vars are set; the runner fills them in.
    ("template_investigation.py", ["--template", "${CMDZERO_TEST_TEMPLATE_ID}"]),
    ("alert_investigation.py", ["--demo"]),
    # automated_remediation.py contain requires an existing investigation id
    # and a subject — supplied via env vars filled by the runner.
    (
        "automated_remediation.py",
        [
            "contain",
            "${CMDZERO_TEST_INVESTIGATION_ID}",
            "--subject",
            "${CMDZERO_TEST_SUBJECT}",
            "--template-name",
            "${CMDZERO_TEST_REMEDIATION_TEMPLATE}",
        ],
    ),
]
```

- [ ] **Step 2: Add an abort helper and an env-substitution helper**

Insert above `main()`:

```python
def _expand_env(args: list[str]) -> tuple[list[str], str | None]:
    """Replace ${ENV_VAR} placeholders in args. If any placeholder is
    unset, return (args, reason_to_skip)."""
    import os
    expanded: list[str] = []
    for a in args:
        m = re.fullmatch(r"\$\{([A-Z_][A-Z0-9_]*)\}", a)
        if m:
            val = os.environ.get(m.group(1))
            if not val:
                return args, f"env var {m.group(1)} not set"
            expanded.append(val)
        else:
            expanded.append(a)
    return expanded, None


def _read_phase_aborts_mutate(results: list[RunResult]) -> bool:
    """If every read-only run failed with an auth-shaped error, abort
    before running mutations."""
    auth_failures = [
        r for r in results
        if r.script in READ_ONLY_SCRIPTS
        and r.exit_code != 0
        and ("403" in r.stderr_tail or "401" in r.stderr_tail or "unauthorized" in r.stderr_tail.lower())
    ]
    return len(auth_failures) >= 3
```

- [ ] **Step 3: Wire the mutate phase into `main()`**

Append after the read-only phase block in `main()`:

```python
    # Phase: mutate
    if args.phase in ("mutate", "all"):
        if _read_phase_aborts_mutate(results):
            print(
                "ABORT: too many auth failures in read-only phase — "
                "skipping mutating runs.",
                file=sys.stderr,
            )
        else:
            for script, run_args in MUTATING_INVOCATIONS:
                expanded, skip_reason = _expand_env(run_args)
                if skip_reason:
                    # Record a skipped row so the report shows what we
                    # didn't run and why.
                    results.append(
                        RunResult(
                            script=script,
                            args=run_args,
                            exit_code=-2,
                            duration_s=0.0,
                            stdout_tail="",
                            stderr_tail=f"[skipped: {skip_reason}]",
                        )
                    )
                    continue
                results.append(run_one(script, expanded, timeout=120))
```

- [ ] **Step 4: Run the mutate phase**

The mutating runs need a real template id, an existing investigation id, a subject, and a remediation template name to be specified as env vars. Set what's available; the rest get logged as skipped:

```bash
# Example — fill in real IDs from your warniCo tenant before running.
export CMDZERO_TEST_TEMPLATE_ID="<inv-template-uuid>"
# Optionally:
# export CMDZERO_TEST_INVESTIGATION_ID="<existing-inv-uuid>"
# export CMDZERO_TEST_SUBJECT="user:alice@example.com"
# export CMDZERO_TEST_REMEDIATION_TEMPLATE="<rem-template-name>"

python run_all_scripts.py --phase mutate
```

Expected: any invocation whose env vars are set runs and exits 0; the rest appear in the report with `exit_code=-2` and `[skipped: env var ... not set]` in `stderr_tail`. Created investigation IDs and remediation IDs appear in the report.

- [ ] **Step 5: Commit**

```bash
git add run_all_scripts.py script_run_report.json script_run_report.md
git commit -m "feat(runner): add mutating phase with abort guard and env substitution

Mutating invocations require real IDs from the live tenant supplied via
env vars; missing vars produce a [skipped] row instead of a hard error.
The read-only phase serves as an auth-health check — three or more
auth failures abort the mutate phase entirely."
```

---

### Task 18: End-to-end run

- [ ] **Step 1: Run the full SDK test suite plus all phases of the runner**

```bash
cd sdk && python -m pytest tests/ -v
cd ..
python run_all_scripts.py --phase all
```

Expected:
- All SDK tests pass in <10 seconds
- All `--help` rows exit 0
- All read-only rows exit 0
- Any mutating rows where the required env var is set exit 0; created investigation/remediation IDs are recorded in the report

- [ ] **Step 2: Inspect the final report**

Run: `cat script_run_report.md`
Confirm: every script appears at least once; no unexplained failures.

- [ ] **Step 3: Final commit (optional — only if the previous run produced changes to the report files)**

```bash
git add -A
git status
git diff --cached
```

If any new untracked files (e.g., new fixture files captured) or report-file changes are pending, commit them. Otherwise nothing to do.

```bash
git commit -m "chore: end-to-end run report for the test suite and live runner"
```

---

## Phase 5 — Optional follow-up

### Task 19 (optional): Update CLAUDE.md to remove the stale Atlas note for the public API

**Files:**
- Modify: `/Users/ehulse/.claude/CLAUDE.md` (the `## API Integration Defaults` section)

Per the verified probes (kebab-case wins for the public API), the line `Investigation templates endpoint is /investigationTemplates (camelCase, not kebab; ...)` only applies to Atlas. It needs scoping or removal.

- [ ] **Step 1: Read the current section**

Run: `grep -n "investigationTemplates" /Users/ehulse/.claude/CLAUDE.md`

- [ ] **Step 2: Edit the line to scope it explicitly to Atlas (do not just delete — Atlas users still need the camelCase note)**

Replace:
```
- Investigation templates endpoint is `/investigationTemplates` (camelCase, not kebab; `/investigation-templates` and `/investigations/templates` both 404). Response wraps under `{ids, investigationTemplates, next}`.
```
with:
```
- Atlas API: investigation templates endpoint is `/investigationTemplates` (camelCase, not kebab; `/investigation-templates` and `/investigations/templates` both 404).
- Public API (`api.cmdzero.io/public/v1`): investigation templates endpoint is `/organizations/{org}/investigation-templates` (kebab-case under the org-scoped path). Response wraps under `{investigationTemplates, next, warnings, errors}`.
```

- [ ] **Step 3: No commit — CLAUDE.md is a personal config file and lives outside the repo.**

---

## Summary checklist (work through in order)

- [ ] Task 1 — scaffold `sdk/tests/` with conftest
- [ ] Task 2 — capture live API response fixtures
- [ ] Task 3 — `test_health.py`
- [ ] Task 4 — `test_organizations.py`
- [ ] Task 5 — `test_applications.py`
- [ ] Task 6 — `test_users.py`
- [ ] Task 7 — `test_catalog.py`
- [ ] Task 8 — `test_business_context.py`
- [ ] Task 9 — `test_investigation_templates.py` (regression-anchored)
- [ ] Task 10 — `test_remediation_templates.py` (regression-anchored)
- [ ] Task 11 — `test_investigations.py`
- [ ] Task 12 — `test_remediations.py`
- [ ] Task 13 — `test_pagination.py`
- [ ] Task 14 — `test_errors.py`
- [ ] Task 15 — runner skeleton with `--help` phase
- [ ] Task 16 — runner read-only phase
- [ ] Task 17 — runner mutating phase with abort guard
- [ ] Task 18 — end-to-end run
- [ ] Task 19 — (optional) update CLAUDE.md to disambiguate Atlas vs public API

## Self-review notes

- **Spec coverage:** every section of `2026-04-28-sdk-test-suite-and-live-script-runner-design.md` maps to at least one task above. The spec's "open questions" are pinned in this plan: exception class names are concrete (`UnauthorizedError`, `ForbiddenError`, etc.); `automated_remediation.py`'s flag inventory is verified — no `--dry-run` exists, so the runner uses the read-only `templates` subcommand; `template_investigation.py --list` is verified to exist.
- **Placeholder scan:** no TODO/TBD/handwave in any step. Every code block is complete.
- **Type consistency:** `CommandZero` (not `CmdzeroClient`); resource attributes match the names in `client.py`; exception names match `exceptions.py`.
- **Risk note carried forward:** mutating phase will create real investigations/remediations on `warniCo`. Created IDs are extracted via regex into the report so the user can review and clean up via the SOC dashboard.
