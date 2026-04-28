# Command Zero Recipes

Examples, integrations, and tooling for the [Command Zero](https://cmdzero.io) Public API.

This repository is a starter kit for security teams, MSSPs, and platform engineers who want to drive Command Zero programmatically — kicking off investigations from a SIEM, automating remediation, syncing business context, building dashboards, or wiring Command Zero into agentic / LLM workflows.

## What's in here

| Component | Path | Description |
|---|---|---|
| **Recipe scripts** | `*.py` (repo root) | Self-contained Python examples for common workflows. Each script is runnable on its own. |
| **Python SDK** | [`sdk/`](sdk/) | Typed, synchronous Python client for the Command Zero Public API (v2026-03-12). Pydantic v2 models, automatic retry, lazy pagination. |
| **MCP server** | [`cmdzero-public-api-mcp/`](cmdzero-public-api-mcp/) | Go-based [Model Context Protocol](https://modelcontextprotocol.io) server that exposes Command Zero as tools for Claude and other LLM agents. |

The recipe scripts are intentionally written against a small shared HTTP wrapper ([`cmdzero_client.py`](cmdzero_client.py)) rather than the SDK so the request/response shape is explicit and easy to port to other languages. Use the SDK when you want types and conveniences; use the wrapper or raw HTTP when you want to see exactly what's on the wire.

## Recipe scripts

| Script | What it demonstrates |
|---|---|
| [`alert_investigation.py`](alert_investigation.py) | Submit an alert from a SIEM/SOAR and create or merge into an investigation. Covers built-in alert types, custom alert types with schema, and free-form alerts. |
| [`automated_remediation.py`](automated_remediation.py) | Evaluate a completed investigation's verdict and confidence, then run a matching remediation template against the target subject when thresholds are met. |
| [`business_context.py`](business_context.py) | Manage HR / CMDB business-context uploads — full create / list / replace / delete cycle, including the periodic-sync replace pattern. |
| [`cmdzero_client.py`](cmdzero_client.py) | Shared HTTP client used by the other recipes. Handles bearer auth, 429 retry with backoff, trace-id logging, and pagination. Import from any script. |
| [`health_check.py`](health_check.py) | Confirm API key validity and list every organization the application can access. Suitable for SOAR pre-flight checks or cron uptime probes. |
| [`investigation_pipeline_report.py`](investigation_pipeline_report.py) | Operational reporting — pending investigations by severity, investigations by integration or tag, and SLA latency metrics (p50 / p90 / max / mean). |
| [`mssp_multi_tenant.py`](mssp_multi_tenant.py) | Iterate every organization the API key can access and run per-tenant operations. Built-in `summary` and `assignable-users` commands; generalizes to arbitrary MSSP workflows. |
| [`postback_receiver.py`](postback_receiver.py) | Flask app that receives investigation / remediation completion postbacks. Validates the bearer token, logs the trace ID, and optionally triggers auto-remediation on malicious + high-confidence verdicts. |
| [`sdk_live_test.py`](sdk_live_test.py) | Smoke test that exercises every endpoint the bound application's role can reach using the Python SDK. Reports endpoints denied by role policy (403) as policy, not failure. |
| [`template_investigation.py`](template_investigation.py) | Discover investigation templates and trigger one with leads and an optional time bound (e.g., the HR last-day pattern against a departing employee). |

## Quick start

### Prerequisites

- **Python 3.10+** for the recipe scripts and SDK
- **Go 1.24+** if you want to build the MCP server
- A Command Zero **API key** and **organization ID**, created in the Command Zero console under Application Settings

### Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` covers the recipe scripts:

```
requests>=2.31
flask>=3.0          # postback_receiver.py only
python-dotenv>=1.0  # auto-loads .env at import time
```

The SDK has its own dependencies — see [`sdk/README.md`](sdk/README.md).

### Configure credentials

All scripts and the SDK read credentials from environment variables. **Do not hard-code keys.** Either export them in your shell or place them in a local `.env` file (auto-loaded by `python-dotenv`):

```bash
# .env  (do not commit)
COMMAND_ZERO_API=cz_xxx_your_api_key_here
COMMAND_ZERO_ORG=org_your_organization_id
```

The legacy variable names `CMDZERO_API_KEY` and `CMDZERO_ORG_ID` are also accepted.

### Verify connectivity

```bash
python health_check.py
```

Exit code `0` means the key is valid and the service is reachable.

### Run a recipe

```bash
# Kick off an investigation from an alert payload
python alert_investigation.py --help

# Generate a pipeline report for the last 24 hours
python investigation_pipeline_report.py

# List assignable users across every tenant the key can see
python mssp_multi_tenant.py assignable-users
```

## Python SDK

A typed Python client for the Command Zero Public API lives under [`sdk/`](sdk/).

```bash
pip install -e ./sdk
```

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    cz.health.check()
    for inv in cz.investigations.list(filter="severity eq 'high'"):
        print(inv.id, inv.status, inv.title)
```

The SDK supports every documented endpoint, exposes Pydantic v2 models with snake-case ↔ camel-case aliasing, retries 429s with exponential backoff, and provides lazy pagination iterators. See [`sdk/README.md`](sdk/README.md) and [`sdk/CHANGELOG.md`](sdk/CHANGELOG.md) for details.

## MCP server

The Go-based MCP server in [`cmdzero-public-api-mcp/`](cmdzero-public-api-mcp/) lets Claude and other MCP-aware LLM agents drive Command Zero directly — listing investigations, starting new ones, running remediations, syncing business context, and so on.

```bash
cd cmdzero-public-api-mcp
go build -o cmdzero-public-api-mcp ./cmd/cmdzero-public-api-mcp/

export CMDZERO_API_KEY=...
export CMDZERO_ORG_ID=...

# Stdio mode (Claude Code, Claude Desktop)
./cmdzero-public-api-mcp -t stdio

# HTTP mode
./cmdzero-public-api-mcp -t streamable-http --address localhost:8080
```

The server exposes 25 tools across health, organizations, applications, users, investigation templates, investigations, remediation templates, remediations, business context, and catalog. Tool categories can be selectively enabled or disabled via flags. See [`cmdzero-public-api-mcp/README.md`](cmdzero-public-api-mcp/README.md) for the full tool reference and the bundled Claude skills (`/investigate`, `/triage`, `/remediate`, etc.).

## API documentation

- **API reference:** https://api.cmdzero.io/public/v1/doc
- **Default base URL:** `https://api.cmdzero.io/public/v1`
- **API version covered:** `2026-03-12`
- **Authentication:** Bearer token in the `Authorization` header

## Security notes

- All scripts read credentials from environment variables — never commit your `.env` or any file containing an API key.
- API keys are scoped to a single application and its role; least-privilege those roles in the Command Zero console.
- The recipes log a Command Zero trace ID (`X-Cmdzero-Traceid`) for every request — include it in any support ticket.
- Postback endpoints (see [`postback_receiver.py`](postback_receiver.py)) should be reachable from Command Zero and protected with the same bearer token used for outbound calls.

## License

The Python SDK is proprietary — see [`sdk/LICENSE`](sdk/LICENSE).

The recipe scripts and MCP server are provided as reference implementations for Command Zero customers and partners. Contact your Command Zero representative for licensing terms covering production redistribution or modification.

## Support

- **Documentation:** https://docs.cmdzero.io
- **API reference:** https://api.cmdzero.io/public/v1/doc
- **Issues:** Please contact your Command Zero representative or open a support ticket through the console.
