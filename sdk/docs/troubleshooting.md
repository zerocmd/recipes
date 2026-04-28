# Troubleshooting

Common failure modes and what to do about them. Every API error
carries a `trace_id` — include it when escalating to support.

## `401 — unknown application key`

```text
UnauthorizedError: [401] unknown application key (trace=…)
```

The bearer token is wrong, expired, or revoked. Check:

1. The `COMMAND_ZERO_API` env var (or `api_key=` argument) actually
   contains your full key — not just the fingerprint.
2. The application that owns this key is still enabled in the console.
3. You haven't accidentally URL-encoded the key.

## `403 — path not authorized for this role`

```text
ForbiddenError: [403] path not authorized for this role (trace=…)
```

The application's role doesn't include the path you called.
Role-policy is enforced **per (HTTP method, path) pair** — for example,
an `investigator` role typically allows `GET /users` but rejects
`QUERY /users`.

Common offenders:

| Endpoint | Roles that typically work |
|---|---|
| `GET /context/uploads` | administrator |
| `POST /context/uploads` | administrator |
| `GET /investigations/templates` | responder, administrator |
| `GET /remediations/templates` | responder, administrator |
| `POST /remediations` | responder, administrator |
| `QUERY /organizations` | administrator |
| `QUERY /users` | administrator |

If you need broader access:

- **Upgrade the application's role** in the console.
- Or split the workload across multiple applications, each with the
  minimum role for its slice. This follows least-privilege and limits
  blast radius if one key leaks.

## `400 — unknown filter field: "<name>"`

```text
BadRequestError: [400] unknown filter field: "createdBy/name" (trace=…)
```

The filter syntax is valid OData but the **endpoint doesn't allow
filtering on that field**. The OData grammar is broader than the
server's per-endpoint allowlist.

Example: `createdBy/name`, `createdBy/type`, `createdBy/id`,
`templateId`, and `id` are all rejected by `/investigations` even
though the syntax is documented.

See [filtering](filtering.md) for the per-endpoint filterable-field
matrix and recommended workarounds (e.g. tag at create time and
filter by tag).

## `422 — invalid status transition`

```text
UnprocessableEntityError: [422] cannot transition from 'completed' to 'in-progress' (trace=…)
```

Some status changes are forbidden by the workflow rules:

| From | Permitted transitions |
|---|---|
| `pending-review` | `in-progress`, `on-hold`, `completed` |
| `in-progress` | `on-hold`, `completed` |
| `on-hold` | `in-progress`, `completed` |
| `investigating`, `completed`, `failed` | (none — terminal/system) |

The client cannot set `investigating` (automation-only) or `failed`
(system-only). Re-fetch the investigation, then choose a legal
transition.

## `429 — rate limited`

```text
RateLimitError: [429] rate limit exceeded (trace=…)
```

The SDK retries 429s automatically with backoff. You only see this
exception when the retry budget is exhausted (default 5 attempts).

- Increase `max_retries=` if you have headroom.
- Slow down the call rate on your side.
- 429 on `POST /investigations` specifically can mean
  **the org's investigation quota is exhausted**, not just rate
  limiting. Check the response body's `message` field for
  disambiguation.

## `severity=Low` (or other capitalization surprises)

The API documents enum values in lowercase, but production sometimes
returns capitalized variants (`'Low'` instead of `'low'`,
`'Investigators'` instead of `'investigator'`).

The SDK handles this by typing all such fields as `str` rather than
strict `StrEnum`. When you compare against a known value, normalize:

```python
inv = cz.investigations.get(inv_id)

if inv.severity and inv.severity.lower() == "high":
    ...
```

The `Severity`, `Role`, etc. constants in `cmdzero.enums` are still
useful for what-could-it-be, just don't `==` against them blindly.

## Pydantic validation errors on `model_validate`

If you get a `pydantic.ValidationError` when parsing a response, the
server returned a shape the SDK doesn't model. Two flavors:

1. **A required field is missing.** Open an issue — this is an SDK
   bug or a server contract change.
2. **An enum field has a new value.** This shouldn't happen for the
   open enums (typed as `str`) but could for closed ones. Same fix:
   open an issue.

In the meantime, drop down to the raw response:

```python
raw = cz._transport.request("GET", f"/organizations/{org_id}/investigations/{inv_id}")
# raw is a dict; do whatever you need
```

## `httpx.TimeoutException` (or its SDK equivalent `TransportError`)

The request didn't complete in `timeout=` seconds. Either:

- Increase the timeout: `CommandZero(timeout=120.0)`.
- Check whether you're filtering too broadly — large list calls may
  time out where smaller ones succeed.
- If multiple in-flight requests are slow, your pool is starved —
  increase the `httpx.Client` connection-pool limit by passing
  `client=` (see [configuration](configuration.md)).

## Postback isn't firing

Check, in order:

1. The investigation/remediation actually completed (check `status` in
   the console).
2. The configured `postback.url` is reachable from Command Zero's
   egress range (firewall? IP allowlist?).
3. Your receiver returned a 2xx response. Non-2xx triggers retries
   then eventually drops.
4. The bearer token your receiver is checking matches the
   `postback.token` you passed at submission time.

If the postback fires but your handler errors out, check your service
logs — the retry behavior is server-side and not visible client-side.

## What to send to support

When opening a support ticket, include:

- The **trace id** from the failing call (`error.trace_id` on the
  exception, or `X-Cmdzero-Traceid` from the response header).
- The **API key fingerprint** (the part before the second `.`,
  e.g. `c0.f00fee.`) — never the full key.
- The **organization id** the call was scoped to.
- The exact request: HTTP method, path, query params, body shape (not
  values if sensitive).
- The full response body (it includes the structured `Error` shape).

The trace id alone usually lets Command Zero pinpoint your request in
~seconds.
