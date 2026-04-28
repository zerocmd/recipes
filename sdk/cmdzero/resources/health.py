from __future__ import annotations

from ..models import HealthResponse
from .base import BaseResource


class HealthResource(BaseResource):
    """``GET /ok`` — confirms API key validity and service health."""

    def check(self) -> HealthResponse:
        data = self._request("GET", "/ok")
        return HealthResponse.model_validate(data)
