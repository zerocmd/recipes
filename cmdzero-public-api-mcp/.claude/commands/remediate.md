Execute a remediation action in Command Zero.

## Instructions

You are helping the user execute a remediation action against a subject in Command Zero.

**If the user provides a template ID, subject, and justification:**
1. Call `create_remediation` directly with the provided parameters.

**If the user provides a template name or description:**
1. Call `list_remediation_templates` to find matching templates.
2. Present the matches and confirm which template to use.
3. Ask for the subject (type and value) and justification if not provided.
4. Call `create_remediation` with the resolved templateId, subject, and justification.

**If the user is unsure what remediations are available:**
1. Call `list_remediation_templates` and present all available templates with their descriptions, subject types, and whether undo templates exist.

After creating the remediation:
1. Call `get_remediation` with the returned ID to check execution status.
2. Display the remediation status, subject, template used, and any result details.

Important: Always confirm with the user before executing a remediation, as these actions (e.g., disabling user accounts, revoking sessions) have real-world impact.

$ARGUMENTS
