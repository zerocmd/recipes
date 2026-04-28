Show a Command Zero SOC dashboard overview.

## Instructions

You are generating a security operations center (SOC) dashboard view for Command Zero. Gather data from multiple sources and present a consolidated overview.

1. Call these in parallel:
   - `list_investigations` with `limit=50` to get recent investigations
   - `list_remediations` with `limit=20` to get recent remediations
   - `list_users` to get the team roster

2. Present the dashboard with these sections:

**Investigation Summary:**
- Total investigations (all time visible in results)
- Active (non-completed/closed) count
- Breakdown by status: investigating, new, completed, closed
- Breakdown by severity: critical, high, medium, low

**Critical Alerts:**
- List any critical or high severity investigations that are not yet completed
- Highlight unassigned ones

**Recent Remediations:**
- List recent remediations with: template name, subject, status (success/pending/failed), created time
- Count by status

**Team:**
- List users with their roles (administrator, investigator, responder, observer)
- Note which users are currently assigned to active investigations

**Recommendations:**
- Flag any unassigned critical/high investigations
- Note any failed remediations that need attention
- Suggest actions based on the current state

$ARGUMENTS
