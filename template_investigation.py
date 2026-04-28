"""Use case 2: template-based investigation for recurring workflows.

Discovers available investigation templates, then triggers one with a
list of leads. The blog example is the HR last-day pattern: a separation
event from your HRIS fires a `users-last-day` template against the
departing employee's identity, scoped by start/end time.

Env: CMDZERO_API_KEY, CMDZERO_ORG_ID
Run:
  python template_investigation.py --list
  python template_investigation.py --template users-last-day \\
      --lead EMAIL_ADDRESS:departing.employee@company.com \\
      --title "Last day review - J. Smith" \\
      --start 2026-04-01T00:00:00Z --end 2026-04-27T00:00:00Z
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from cmdzero_client import CommandZeroClient, CommandZeroError, configure_logging


def list_templates(client: CommandZeroClient, organization_id: str | None = None) -> list[dict]:
    return list(client.query(client.org_path("/investigation-templates", organization_id)))


def find_template(client: CommandZeroClient, name_or_id: str, organization_id: str | None = None) -> dict | None:
    for tpl in list_templates(client, organization_id):
        if tpl.get("id") == name_or_id or tpl.get("name") == name_or_id:
            return tpl
    return None


def start_template_investigation(
    client: CommandZeroClient,
    *,
    template_id: str,
    leads: list[dict],
    title: str | None = None,
    tags: list[str] | None = None,
    start_time: str | None = None,
    end_time: str | None = None,
    postback_url: str | None = None,
    postback_token: str | None = None,
    organization_id: str | None = None,
) -> dict:
    body: dict[str, Any] = {"templateId": template_id, "leads": leads}
    if title:
        body["title"] = title
    if tags:
        body["tags"] = tags
    if start_time:
        body["startTime"] = start_time
    if end_time:
        body["endTime"] = end_time
    if postback_url:
        body["postback"] = {"url": postback_url, "token": postback_token or ""}
    return client.post(client.org_path("/investigations", organization_id), json=body)


def _parse_lead(arg: str) -> dict:
    if ":" not in arg:
        raise argparse.ArgumentTypeError(f"--lead must be TYPE:value, got {arg!r}")
    type_, value = arg.split(":", 1)
    return {"type": type_.strip(), "value": value.strip()}


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--list", action="store_true", help="List available templates and exit.")
    parser.add_argument("--template", help="Template id or slug name (e.g. users-last-day).")
    parser.add_argument("--lead", action="append", default=[], type=_parse_lead,
                        help="Repeatable. Format TYPE:value, e.g. EMAIL_ADDRESS:user@x.com")
    parser.add_argument("--title")
    parser.add_argument("--tag", action="append", default=[], dest="tags")
    parser.add_argument("--start", dest="start_time", help="ISO-8601 startTime")
    parser.add_argument("--end", dest="end_time", help="ISO-8601 endTime")
    parser.add_argument("--postback-url")
    parser.add_argument("--postback-token")
    args = parser.parse_args()

    client = CommandZeroClient()

    try:
        if args.list:
            for tpl in list_templates(client):
                accepts = ",".join(tpl.get("leadTypes") or []) or "—"
                print(f"  {tpl.get('name', tpl['id']):<30}  leads=[{accepts}]  {tpl.get('title','')}")
            return 0

        if not args.template or not args.lead:
            parser.error("--template and at least one --lead are required (or use --list)")

        result = start_template_investigation(
            client,
            template_id=args.template,
            leads=args.lead,
            title=args.title,
            tags=args.tags or None,
            start_time=args.start_time,
            end_time=args.end_time,
            postback_url=args.postback_url,
            postback_token=args.postback_token,
        )
        print(f"Investigation {result.get('id')}  action={result.get('action')}")
        print(f"Console: {result.get('consoleUrl', '')}")
        return 0
    except CommandZeroError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
