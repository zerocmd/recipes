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
    sample = fixture("remediation_templates_list")["remediationTemplates"][0]
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

    list(client.remediation_templates.for_subject_type("MICROSOFT_ENTRA_USER"))
    assert route.called
    sent_filter = route.calls[0].request.url.params.get("filter")
    assert sent_filter == "subjectType eq 'MICROSOFT_ENTRA_USER'"


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
