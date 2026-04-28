# Command Zero Python SDK — documentation

Welcome. This is the deep-dive companion to the project [README](../README.md).

## Concepts

| | |
|---|---|
| [Getting started](getting-started.md) | Install, first call, the 5-minute tour |
| [Authentication](authentication.md) | API keys, application roles, the role-vs-endpoint matrix |
| [Configuration](configuration.md) | Env vars, base URL, timeouts, retries, BYO `httpx.Client` |
| [Filtering](filtering.md) | OData operators, what's actually filterable per endpoint |
| [Pagination](pagination.md) | `next` cursor model, GET vs QUERY, materializing |
| [Error handling](error-handling.md) | Exception hierarchy, trace ids, retry policy |
| [Postbacks](postbacks.md) | Receiving completion webhooks, payload shapes, Flask receiver |
| [Troubleshooting](troubleshooting.md) | Common failures, what to send to support |

## Resource reference

One page per resource group, each with the full method surface, the
models it returns, and the role/permission notes.

| | |
|---|---|
| [`cz.health`](resources/health.md) | API health probe |
| [`cz.organizations`](resources/organizations.md) | Orgs the application can act against |
| [`cz.applications`](resources/applications.md) | Application metadata + role assignments |
| [`cz.users`](resources/users.md) | User directory + assignable filter |
| [`cz.catalog`](resources/catalog.md) | Subject-type catalog used in alert/business-context schemas |
| [`cz.business_context`](resources/business-context.md) | HR / CMDB upload lifecycle |
| [`cz.investigation_templates`](resources/investigation-templates.md) | Pre-configured investigation patterns |
| [`cz.investigations`](resources/investigations.md) | Investigation CRUD, alert + template creation, status updates |
| [`cz.remediation_templates`](resources/remediation-templates.md) | Remediation actions + undo |
| [`cz.remediations`](resources/remediations.md) | Execute remediations, track outcome |

## End-to-end use cases

| | |
|---|---|
| [Alert ingestion](examples/alert-ingestion.md) | SIEM/SOAR alert → investigation → postback |
| [Template investigations](examples/template-investigations.md) | HR last-day, separation, dormant-account reviews |
| [Business context sync](examples/business-context-sync.md) | Periodic HR + CMDB upload with PUT replacement |
| [Automated remediation](examples/automated-remediation.md) | Postback → verdict → remediate → close |
| [Pipeline reporting](examples/pipeline-reporting.md) | Operational queries, SLA latency reports |
| [MSSP multi-tenant](examples/mssp-multi-tenant.md) | Per-org operations across an MSSP customer base |

## Reading order

If you're new, follow this path:

1. [Getting started](getting-started.md)
2. [Authentication](authentication.md)
3. [Filtering](filtering.md) and [pagination](pagination.md)
4. [Error handling](error-handling.md)
5. The example matching your use case
6. The resource reference for each `cz.<thing>` you actually call
