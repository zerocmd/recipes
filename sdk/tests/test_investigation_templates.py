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
