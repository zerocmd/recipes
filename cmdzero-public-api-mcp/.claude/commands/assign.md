Assign a Command Zero investigation to a user.

## Instructions

You are helping the user assign an investigation to one or more analysts.

1. If a user name or email is provided but not a user ID:
   - Call `list_users` with a filter like `contains(name, '<name>')` or `contains(email, '<email>')` to find the user.
   - If multiple matches, present them and ask which one.

2. If no user is specified:
   - Call `list_users` with filter `role ne 'observer'` to show assignable users.
   - Let the user choose.

3. Call `get_investigation` with the investigation ID to see current assignees.

4. Determine the updated assignee list:
   - If adding: append the new user ID to the existing assignees list.
   - If replacing: use only the new user IDs.
   - Confirm with the user.

5. Call `update_investigation` with the `investigationId` and `assignees` array.

6. Confirm the assignment by showing the updated investigation's assignee list.

$ARGUMENTS
