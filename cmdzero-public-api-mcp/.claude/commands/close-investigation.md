Close a Command Zero investigation.

## Instructions

You are helping the user close an investigation after review and/or remediation.

1. Call `get_investigation` with the provided investigation ID to verify current status.

2. If the investigation is already completed or closed, inform the user.

3. If the investigation is still active:
   - Ask for a final status: "completed" (investigation done) or "closed" (no further action needed).
   - Ask for any final tags to apply (e.g., "remediated", "false-positive", "escalated").
   - Ask for category update if not already set.

4. Call `update_investigation` with:
   - `investigationId`
   - `status`: the chosen status
   - `tags`: final tags (if provided)
   - `category`: if updated
   - Any other fields the user wants to update

5. Display the final investigation state confirming closure.

Note: Status transitions are validated by Command Zero. For example, you cannot move from "completed" back to "investigating". If the update fails with a 422 error, explain the valid transitions to the user.

$ARGUMENTS
