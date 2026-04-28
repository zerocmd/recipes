Triage active Command Zero investigations.

## Instructions

You are helping the user triage and prioritize security investigations in Command Zero.

1. Call `list_investigations` with filter `status ne 'completed' and status ne 'closed'` and `limit=50` to get active investigations.
2. If no active investigations are found, also try without the filter to show recent completed ones.

Present a summary organized by severity (critical first, then high, medium, low):

For each investigation, show:
- Title
- Status (investigating, new, etc.)
- Severity
- Assignees (or "UNASSIGNED" in bold if none)
- Created time (relative, e.g., "2 hours ago")
- Category (if set)
- Tags

At the end, provide aggregate stats:
- Total active investigations
- Breakdown by severity
- Breakdown by status
- Count of unassigned investigations (highlight if > 0)
- Any critical severity investigations that need immediate attention

$ARGUMENTS
