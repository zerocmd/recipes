# Error handling

Every API failure raises a typed subclass of `CommandZeroError`. The
class is chosen from the HTTP status code; the original error response
body and `X-Cmdzero-Traceid` header are preserved as attributes.

## Exception hierarchy

```text
CommandZeroError                   ← catch this for "any API failure"
├── TransportError                 ← network failure, timeout, DNS error (status=0)
├── BadRequestError                ← 400 — malformed request
├── UnauthorizedError              ← 401 — bad/missing API key
├── ForbiddenError                 ← 403 — role lacks permission for the path
├── NotFoundError                  ← 404 — the resource does not exist
├── ConflictError                  ← 409 — request conflicts with current state
├── UnprocessableEntityError       ← 422 — semantically invalid (e.g. illegal status transition)
├── RateLimitError                 ← 429 — rate limit hit, or org quota exhausted
└── ServerError                    ← 5xx — Command Zero failed to process
```

## Attributes

Every exception carries:

| Attribute | Type | Description |
|---|---|---|
| `status` | `int` | HTTP status code (`0` for transport failures) |
| `message` | `str` | Human-readable error description from the response body |
| `trace_id` | `str \| None` | Value of the `X-Cmdzero-Traceid` response header |
| `type` | `str \| None` | HTTP status text (`"Bad Request"`, `"Forbidden"`, …) |
| `body` | `Any` | Parsed JSON body, or raw text if not JSON |

`RateLimitError` additionally carries:

| Attribute | Type | Description |
|---|---|---|
| `retry_after` | `float \| None` | Value of the `Retry-After` header in seconds, when present |

## Catching

```python
from cmdzero import (
    CommandZero,
    CommandZeroError,
    NotFoundError,
    ForbiddenError,
    RateLimitError,
    UnprocessableEntityError,
)

with CommandZero() as cz:
    try:
        cz.investigations.update(inv_id, status="investigating")
    except UnprocessableEntityError as e:
        # the API rejects this status transition (e.g. "investigating" is system-only)
        log.warning("invalid transition trace=%s msg=%s", e.trace_id, e.message)
    except ForbiddenError as e:
        log.error("role lacks permission trace=%s", e.trace_id)
    except NotFoundError:
        log.warning("investigation %s no longer exists", inv_id)
    except RateLimitError as e:
        log.warning("throttled retry_after=%s trace=%s", e.retry_after, e.trace_id)
    except CommandZeroError as e:
        log.exception("unexpected API failure status=%s trace=%s", e.status, e.trace_id)
```

## Trace ids

Every successful **and** failed response carries
`X-Cmdzero-Traceid`. The SDK exposes it as `error.trace_id` on every
exception. Include it in any support escalation — Command Zero can
locate your specific request in their logs from the trace id.

To capture the trace id on success too, you'll need to inspect the
response yourself. The cleanest way is via a custom `httpx.Client`
event hook:

```python
import httpx, logging

log = logging.getLogger("cmdzero.trace")

def log_trace(response: httpx.Response):
    tid = response.headers.get("X-Cmdzero-Traceid")
    if tid:
        log.debug("%s %s -> %d trace=%s",
                  response.request.method, response.request.url, response.status_code, tid)

client = httpx.Client(event_hooks={"response": [log_trace]})
cz = CommandZero(client=client)
```

## Retries

The SDK retries automatically on **429 only**, with exponential
backoff (base 1s, cap 30s) that honors the `Retry-After` header when
present. Default budget is 5 attempts.

Other 4xx and 5xx responses are **not** retried — POST mutations
aren't idempotent, and a blind retry could double-submit
investigations or remediations. If you need to retry a failed
mutation, do so with knowledge of what state changed.

To tune the retry budget:

```python
cz = CommandZero(max_retries=10)        # patient batch
cz = CommandZero(max_retries=1)         # interactive paths fail fast
```

When the retry budget is exhausted, the final 429 propagates as
`RateLimitError`.

## Network failures

`httpx`-level failures — DNS, connection refused, TLS errors, timeouts
— map to `TransportError`. The `__cause__` attribute holds the
original `httpx.HTTPError` for debugging:

```python
from cmdzero import TransportError

try:
    cz.health.check()
except TransportError as e:
    log.error("network failure: %s (cause: %s)", e, e.__cause__)
```

`TransportError.status` is `0`. `trace_id` is `None` (no response was
received).

## Body inspection

The full error body is preserved on `error.body` for ad-hoc debugging:

```python
try:
    cz.investigations.list(filter="bogusField eq 'x'")
except BadRequestError as e:
    print(e.body)
    # {'message': 'unknown filter field: "bogusField"', 'status': 400,
    #  'traceId': '…', 'type': 'Bad Request'}
```

## When the API returns success but something is wrong

Some list endpoints include `errors` and `warnings` arrays in the
envelope alongside the items. The SDK exposes them on the
list-response models (`ListInvestigationsResponse.errors`, etc.) but
the `PaginatedIterator` strips them away in favor of yielding items
only. To inspect them, drop down to the transport:

```python
raw = cz._transport.request("GET", f"/organizations/{org_id}/investigations?limit=1")
print(raw.get("warnings"), raw.get("errors"))
```

(Underscore-prefix means "internal" — accept the breakage risk.)
