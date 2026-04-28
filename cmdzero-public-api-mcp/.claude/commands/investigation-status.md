Check the status of a Command Zero investigation.

## Instructions

You are helping the user check the status and details of a specific investigation.

1. Call `get_investigation` with the provided investigation ID.
2. Display a comprehensive summary:

**Investigation Overview:**
- Title
- ID
- Status (with visual indicator: investigating, completed, closed, etc.)
- Severity and Sensitivity
- Category
- Console URL

**People:**
- Assignees (names)
- Created by (name and type)

**Timeline:**
- Created time
- Start time
- Completed time (if applicable)
- Closed time (if applicable)

**Findings** (if investigation is complete):
- Verdict
- Summary (formatted markdown)
- Observables discovered

**Alerts:**
- List of associated alerts with their action status (investigated vs ignored)

**Tags:**
- All tags applied

If the investigation is still in progress, suggest next steps (wait for completion, assign to analyst, etc.).

$ARGUMENTS
