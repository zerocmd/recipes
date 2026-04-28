# Pipeline reporting & SLA tracking

Use case: build operational reporting on the investigation pipeline.
Who's stuck waiting for review? How long are investigations taking
end-to-end? How long are analysts taking to close once Command Zero
hands them a finding?

The list endpoint accepts OData-flavored filters, and every
investigation carries `created_time`, `completed_time`, and
`closed_time` — enough to power most operational dashboards.

## Pending review by severity

```python
from cmdzero import CommandZero

with CommandZero() as cz:
    pending = cz.investigations.list(
        filter="status eq 'pending-review' and severity in ('high', 'critical')",
    )
    for inv in pending:
        print(inv.id, inv.severity, inv.title)
```

For a real dashboard, you typically want counts:

```python
from collections import Counter

with CommandZero() as cz:
    by_sev = Counter()
    for inv in cz.investigations.list(filter="status eq 'pending-review'"):
        sev = (inv.severity or "unknown").lower()
        by_sev[sev] += 1
    for sev, n in sorted(by_sev.items()):
        print(f"{sev:<13}  {n}")
```

## By tag — campaign tracking

If you tag investigations at create time (with a campaign label, an
integration name, or an alert source identifier), filter by tag to
pull them all back:

```python
campaign = cz.investigations.list(
    filter="'apt-campaign-2026' in tags and status ne 'completed'",
)
```

This is also the recommended workaround for **"investigations created
by my SIEM integration"** — `createdBy/*` paths aren't filterable on
this endpoint, so tag at create time and filter by tag:

```python
# at submission
cz.investigations.create_from_alert(..., tags=["siem-integration", "acme-soar"])

# later
mine = cz.investigations.list(filter="'acme-soar' in tags")
```

## SLA latency report

Time-to-investigate-complete and time-to-analyst-close are two
distinct measures, both useful:

```python
from datetime import datetime
import statistics

def parse_iso(value):
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value

def seconds_between(start, end):
    s, e = parse_iso(start), parse_iso(end)
    if not s or not e:
        return None
    return (e - s).total_seconds()

with CommandZero() as cz:
    investigate_secs = []
    review_secs = []
    for inv in cz.investigations.list(
        filter="status eq 'completed' and createdTime ge 2026-04-01T00:00:00Z",
    ):
        if dt := seconds_between(inv.created_time, inv.completed_time):
            investigate_secs.append(dt)
        if dt := seconds_between(inv.completed_time, inv.closed_time):
            if dt >= 0:
                review_secs.append(dt)

def report(label, samples):
    if not samples:
        return f"{label}: no samples"
    s = sorted(samples)
    return (f"{label}: n={len(s)}  "
            f"p50={s[len(s)//2]:.0f}s  "
            f"p90={s[int(0.9 * (len(s) - 1))]:.0f}s  "
            f"max={s[-1]:.0f}s  "
            f"mean={statistics.fmean(s):.0f}s")

print(report("time to investigate", investigate_secs))
print(report("time to analyst close", review_secs))
```

The difference between `completed_time → closed_time` is one of the
cleaner measures of how quickly analysts process what the automation
delivers. If that gap grows, your team is bottlenecked even if the
investigation pipeline is healthy.

## Filters that work

From production tests, these filters are accepted on `/investigations`:

```python
"status eq 'pending-review'"
"status in ('pending-review', 'in-progress')"
"severity eq 'high'"
"severity in ('high', 'critical')"
"sensitivity eq 'amber'"
"category eq 'BUSINESS-EMAIL-COMPROMISE-(BEC)'"
"type eq 'alert'"
"contains(title, 'phishing')"
"startswith(title, 'CTI')"
"'campaign-x' in tags"
"createdTime ge 2026-04-01T00:00:00Z"
"completedTime ge 2026-04-01T00:00:00Z and closedTime lt 2026-04-15T00:00:00Z"
```

Combine with `and` / `or` / `not` and parentheses.

## Filters that don't work

These are documented in the OData syntax reference but **rejected** by
the `/investigations` endpoint with `400 unknown filter field`:

- `createdBy/name`, `createdBy/type`, `createdBy/id`
- `templateId`
- `id` (use `cz.investigations.get(id)` instead)

See [filtering](../filtering.md) for the per-endpoint matrix.

## Reference scripts

- [`investigation_pipeline_report.py`](../../../investigation_pipeline_report.py) —
  CLI with subcommands `pending-review`, `by-tag`, `by-application`,
  `sla`, `custom --filter "…"`.

## Permissions

`GET /investigations` and `QUERY /investigations` are typically open
to `observer` or above.

## Notes

- `closed_time` may be missing on investigations that completed
  automatically without analyst review.
- `completed_time` is set by Command Zero when the automation finishes;
  `closed_time` is set when an analyst (or your integration) PATCHes
  the status to `completed`.
- Be careful with very broad filters — `status ne 'completed'` against
  a large org returns thousands of rows. Cap with `limit=` if you only
  need a sample.
