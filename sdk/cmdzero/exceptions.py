"""Exception hierarchy for the Command Zero SDK.

Every API failure raises a CommandZeroError subclass. The class is chosen
from the HTTP status; the original Error response body and X-Cmdzero-Traceid
header are exposed as attributes for support escalation.
"""
from __future__ import annotations

from typing import Any


class CommandZeroError(Exception):
    """Base for every error raised by the SDK."""

    def __init__(
        self,
        status: int,
        message: str,
        *,
        trace_id: str | None = None,
        type: str | None = None,
        body: Any = None,
    ):
        super().__init__(f"[{status}] {message} (trace={trace_id})")
        self.status = status
        self.message = message
        self.trace_id = trace_id
        self.type = type
        self.body = body


class TransportError(CommandZeroError):
    """Network failure, timeout, or other non-HTTP error."""

    def __init__(self, message: str, *, cause: Exception | None = None):
        super().__init__(0, message)
        self.__cause__ = cause


class BadRequestError(CommandZeroError):
    """400 — request was malformed or contained invalid parameters."""


class UnauthorizedError(CommandZeroError):
    """401 — API key is missing, invalid, or expired."""


class ForbiddenError(CommandZeroError):
    """403 — caller lacks permission for the resource."""


class NotFoundError(CommandZeroError):
    """404 — the requested resource does not exist."""


class ConflictError(CommandZeroError):
    """409 — request conflicts with current state."""


class UnprocessableEntityError(CommandZeroError):
    """422 — semantically invalid (e.g. illegal investigation status transition)."""


class RateLimitError(CommandZeroError):
    """429 — rate limit hit or per-org quota exhausted.

    The retry_after attribute (seconds, when available) reflects the
    Retry-After header.
    """

    def __init__(self, *args, retry_after: float | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class ServerError(CommandZeroError):
    """5xx — Command Zero failed to process the request."""


_STATUS_TO_EXC: dict[int, type[CommandZeroError]] = {
    400: BadRequestError,
    401: UnauthorizedError,
    403: ForbiddenError,
    404: NotFoundError,
    409: ConflictError,
    422: UnprocessableEntityError,
    429: RateLimitError,
}


def from_status(status: int) -> type[CommandZeroError]:
    if status in _STATUS_TO_EXC:
        return _STATUS_TO_EXC[status]
    if status >= 500:
        return ServerError
    return CommandZeroError
