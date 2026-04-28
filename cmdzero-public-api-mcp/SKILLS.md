---
name: command-skill
description: Uses the commands and abilities for the command zero public apis into the command zero platform. 
---

## Quick Reference

| Skill | What it does | Example |
|---|---|---|
| `/investigate` | Start a new investigation | `/investigate phishing email from jdoe@evil.com with SHA256 275a021bbf...` |
| `/triage` | View & prioritize active investigations | `/triage` |
| `/soc-dashboard` | Full SOC overview dashboard | `/soc-dashboard` |
| `/investigation-status` | Check a specific investigation | `/investigation-status f47ac10b-58cc-...` |
| `/assign` | Assign investigation to analyst | `/assign f47ac10b to Sarah Kim` |
| `/remediate` | Execute a remediation action | `/remediate disable user jmaldive@warnicorp.com` |
| `/close-investigation` | Close with status and tags | `/close-investigation f47ac10b as completed` |

---

## Detailed Usage

### /investigate

Start an investigation from an alert, template, or raw data.

```
# From a template
/investigate using employee-separation template for user jdoe@company.com

# From raw alert data
/investigate suspicious login from IP 203.0.113.42 targeting admin@company.com

# With full alert JSON
/investigate {"alertType": "EmailMalware", "alertData": {"sender": {"email": "attacker@evil.com"}, "file": {"sha256": "275a021bbf..."}}}

# Browse available templates first
/investigate what templates are available?
```

### /triage

Pull up active investigations sorted by severity. Highlights unassigned and critical items.

```
# Basic triage
/triage

# The skill automatically:
# - Filters out completed/closed investigations
# - Sorts by severity (critical → high → medium → low)
# - Flags unassigned investigations
# - Shows aggregate stats
```

### /soc-dashboard

Consolidated SOC view pulling from investigations, remediations, and users.

```
/soc-dashboard

# Shows:
# - Investigation counts by status and severity
# - Critical/high unassigned investigations
# - Recent remediation activity
# - Team roster with current assignments
# - Actionable recommendations
```

### /investigation-status

Deep dive into a specific investigation's findings.

```
/investigation-status f47ac10b-58cc-4670-a46d-2b3132313066

# Shows: verdict, summary, observables, alerts, timeline, assignees, tags
```

### /assign

Assign investigations to analysts.

```
# By name
/assign f47ac10b to Sarah Kim

# By email
/assign f47ac10b to sarah.kim@company.com

# Browse assignable users first
/assign f47ac10b

# Add to existing assignees
/assign add James Chen to f47ac10b
```

### /remediate

Execute remediation actions (disable users, revoke sessions, etc.).

```
# Direct remediation
/remediate disable user jmaldive@warnicorp.com because "Malware distribution confirmed"

# Browse available actions
/remediate what can I do?

# With specific template
/remediate template r-39a26e0p32mi against MICROSOFT_ENTRA_USER jmaldive@warnicorp.com
```

### /close-investigation

Close an investigation after review/remediation.

```
# Close as completed with tags
/close-investigation f47ac10b as completed with tags email-threat, remediated

# Close as no action needed
/close-investigation f47ac10b as closed - false positive
```

---

## Direct MCP Tool Usage

You can also use the underlying MCP tools directly without skills:

```
# Health check
"Check if Command Zero is connected"

# List all users
"Show me all users in my C0 org"

# Query investigations with OData filters
"Find all investigations created this week with severity critical"

# Upload business context
"Upload VIP user list: CEO jane@co.com, CFO bob@co.com"

# Browse catalog types
"What alert schemas does Command Zero support?"

# List remediation templates
"What remediation actions are available?"
```

---

## Common Workflows

### Alert Response
```
/investigate → /investigation-status → /assign → /remediate → /close-investigation
```

### Morning Triage
```
/soc-dashboard → /triage → /assign (for unassigned)
```

### Incident Response
```
/investigate (start) → /investigation-status (poll) → /remediate (contain) → /close-investigation (wrap up)
```
