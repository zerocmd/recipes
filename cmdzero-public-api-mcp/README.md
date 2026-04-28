# Command Zero Public API MCP Server

An MCP (Model Context Protocol) server for the [Command Zero Public API](https://api.cmdzero.io/public/v1) — an automated security investigation platform.

## Prerequisites

- Go 1.24+
- A Command Zero API key (created in the Command Zero console)
- Your organization ID

## Configuration

Set these environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `CMDZERO_API_KEY` | Yes | Your Command Zero API key (Bearer token) |
| `CMDZERO_ORG_ID` | Yes | Organization ID for API calls |
| `CMDZERO_URL` | No | API base URL (default: `https://api.cmdzero.io/public/v1`) |

## Usage

### Build

```bash
go build -o cmdzero-public-api-mcp ./cmd/cmdzero-public-api-mcp/
```

### Run (stdio transport)

```bash
export CMDZERO_API_KEY="c0.your-api-key"
export CMDZERO_ORG_ID="your-org-id"
./cmdzero-public-api-mcp -t stdio
```

### Run (HTTP transport)

```bash
./cmdzero-public-api-mcp -t streamable-http --address localhost:8080
```

### Claude Code MCP Configuration

Add to your Claude Code settings (`~/.claude/settings.json` or project `.claude/settings.json`):

```json
{
  "mcpServers": {
    "cmdzero": {
      "command": "/Users/ehulse/Documents/cmdzero/src/mcp/cmdzero-public-api-mcp/cmdzero-public-api-mcp",
      "args": ["-t", "stdio"],
      "env": {
        "CMDZERO_API_KEY": "c0.your-api-key",
        "CMDZERO_ORG_ID": "your-org-id"
      }
    }
  }
}
```

## Tools (25)

### Health
- `check_health` — Verify API connectivity and authentication

### Organizations
- `list_organizations` — List accessible organizations

### Applications
- `list_applications` — List API applications
- `get_application` — Get application details

### Users
- `list_users` — List users (with OData filtering)
- `get_user` — Get user details

### Investigations
- `list_investigation_templates` — Browse investigation templates
- `get_investigation_template` — Get template details
- `list_investigations` — List investigations (with OData filtering)
- `query_investigations` — Query investigations with complex filters (JSON body)
- `start_investigation` — Start from alert data or template
- `get_investigation` — Get investigation status, verdict, and summary
- `update_investigation` — Update status, assignees, tags, severity

### Remediations
- `list_remediation_templates` — Browse available remediation actions
- `get_remediation_template` — Get template details
- `list_remediations` — List executed remediations
- `create_remediation` — Execute a remediation action
- `get_remediation` — Check remediation execution status

### Business Context
- `list_business_context_uploads` — List context uploads
- `upload_business_context` — Upload organizational context
- `get_business_context_upload` — Get upload details
- `replace_business_context_upload` — Replace upload contents
- `delete_business_context_upload` — Delete an upload

### Catalog
- `list_catalog_types` — Browse alert schema types
- `get_catalog_type` — Get type details

## Claude Skills

When working in this project directory, these slash commands are available:

| Command | Description |
|---------|-------------|
| `/investigate` | Start an investigation from alert data or template |
| `/triage` | Triage and prioritize active investigations |
| `/remediate` | Execute a remediation action |
| `/investigation-status` | Check investigation details and findings |
| `/assign` | Assign an investigation to an analyst |
| `/close-investigation` | Close an investigation with final status |
| `/soc-dashboard` | SOC overview of investigations, remediations, and team |

## CLI Flags

```
-t, --transport        Transport type: stdio or streamable-http (default: stdio)
--address              Address for HTTP server (default: localhost:8080)
--endpoint-path        HTTP endpoint path (default: /mcp)
--log-level            Log level: debug, info, warn, error (default: info)
--version              Print version and exit
--enabled-tools        Comma-separated list of enabled tool categories
--disable-{category}   Disable a specific tool category
```

## Disabling Tool Categories

```bash
# Only enable investigations and remediations
./cmdzero-public-api-mcp --enabled-tools investigations,remediations

# Disable business context tools
./cmdzero-public-api-mcp --disable-business-context
```
