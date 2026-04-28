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
