Start a Command Zero investigation.

## Instructions

You are helping the user start a security investigation in Command Zero using the MCP tools.

**If the user provides alert data or an alert type:**
1. Call `start_investigation` with the provided `alertType` and `alertData`. If the user also provides schema annotations, include `alertSchema`.
2. Call `get_investigation` with the returned investigation ID to confirm creation and show initial status.

**If the user provides a template name:**
1. Call `list_investigation_templates` to find the matching template.
2. Ask the user for leads (subjects to investigate) if not already provided.
3. Call `start_investigation` with `templateId` and `leads`.
4. Call `get_investigation` to confirm and show status.

**If the user is unsure:**
1. Call `list_investigation_templates` and present available templates with descriptions.
2. Let the user choose a template or provide raw alert data.

After starting the investigation, display:
- Investigation ID
- Status
- Title
- Whether it was newly created or merged into an existing investigation
- Console URL (if available)
- Next steps (e.g., "Poll with get_investigation to check progress" or "Assign to an analyst with update_investigation")

$ARGUMENTS
