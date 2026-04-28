"""Use case 3: business context uploads (HR / CMDB).

Wraps the create / list / replace / delete cycle on the business-context
endpoints. The blog calls out two main feeds:

  * HR directory upload — VIP status, department, manager chain.
  * CMDB upload — asset criticality, environment, ownership, compliance scope.

The replace workflow is designed for periodic sync: when your HRIS produces
its weekly delta, PUT the full current dataset to the existing upload id.
The previous version remains active for in-flight investigations until the
new data is processed.

Env: CMDZERO_API_KEY, CMDZERO_ORG_ID
Run:
  python business_context.py list
  python business_context.py upload-hr --name "HR Directory"
  python business_context.py upload-cmdb --name "CMDB Snapshot"
  python business_context.py replace <upload-id> --kind hr
  python business_context.py delete <upload-id>
"""
from __future__ import annotations

import argparse
import sys
from typing import Any

from cmdzero_client import CommandZeroClient, CommandZeroError, configure_logging


HR_SCHEMA = [
    {"path": "email", "type": "EMAIL_ADDRESS"},
    {"path": "manager", "type": "EMAIL_ADDRESS"},
]

CMDB_SCHEMA = [
    {"path": "hostname", "type": "HOST_NAME"},
    {"path": "ip", "type": "IP_ADDRESS"},
    {"path": "owner", "type": "EMAIL_ADDRESS"},
]


def sample_hr_records() -> list[dict]:
    return [
        {
            "email": "sarah.kim@company.com",
            "department": "Engineering",
            "title": "VP of Engineering",
            "manager": "cto@company.com",
            "vip": True,
            "employeeType": "full-time",
        },
        {
            "email": "mike.jones@company.com",
            "department": "Finance",
            "title": "Financial Analyst",
            "manager": "cfo@company.com",
            "vip": False,
            "employeeType": "full-time",
        },
    ]


def sample_cmdb_records() -> list[dict]:
    return [
        {
            "hostname": "db-prod-01.internal",
            "ip": "10.20.1.50",
            "environment": "production",
            "criticality": "critical",
            "complianceScope": ["pci", "sox"],
            "owner": "dba-team@company.com",
        },
        {
            "hostname": "ci-runner-04.internal",
            "ip": "10.30.4.21",
            "environment": "staging",
            "criticality": "low",
            "complianceScope": [],
            "owner": "platform@company.com",
        },
    ]


def list_uploads(client: CommandZeroClient, organization_id: str | None = None) -> list[dict]:
    return list(client.query(client.org_path("/business-context/uploads", organization_id)))


def create_upload(
    client: CommandZeroClient,
    *,
    name: str,
    description: str,
    records: list[dict],
    schema: list[dict],
    organization_id: str | None = None,
) -> dict:
    body: dict[str, Any] = {
        "name": name,
        "description": description,
        "records": records,
        "schema": schema,
    }
    return client.post(client.org_path("/business-context/uploads", organization_id), json=body)


def replace_upload(
    client: CommandZeroClient,
    upload_id: str,
    *,
    records: list[dict],
    schema: list[dict],
    name: str | None = None,
    description: str | None = None,
    organization_id: str | None = None,
) -> dict:
    body: dict[str, Any] = {"records": records, "schema": schema}
    if name:
        body["name"] = name
    if description:
        body["description"] = description
    return client.put(client.org_path(f"/business-context/uploads/{upload_id}", organization_id), json=body)


def delete_upload(client: CommandZeroClient, upload_id: str, organization_id: str | None = None) -> None:
    client.delete(client.org_path(f"/business-context/uploads/{upload_id}", organization_id))


def main() -> int:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list")

    upload_hr = sub.add_parser("upload-hr")
    upload_hr.add_argument("--name", default="HR User Directory")
    upload_hr.add_argument("--description", default="Employee context: VIP, department, manager chain")

    upload_cmdb = sub.add_parser("upload-cmdb")
    upload_cmdb.add_argument("--name", default="CMDB Asset Inventory")
    upload_cmdb.add_argument("--description", default="Host criticality, environment, ownership, compliance scope")

    replace = sub.add_parser("replace")
    replace.add_argument("upload_id")
    replace.add_argument("--kind", choices=("hr", "cmdb"), required=True)

    delete = sub.add_parser("delete")
    delete.add_argument("upload_id")

    args = parser.parse_args()
    client = CommandZeroClient()

    try:
        if args.cmd == "list":
            for u in list_uploads(client):
                print(f"  {u['id']}  status={u.get('status'):<10}  records={u.get('recordCount', 0):>6}  {u.get('name', '')}")
            return 0

        if args.cmd == "upload-hr":
            result = create_upload(
                client,
                name=args.name,
                description=args.description,
                records=sample_hr_records(),
                schema=HR_SCHEMA,
            )
            print(f"Uploaded HR context id={result.get('id')} status={result.get('status')}")
            return 0

        if args.cmd == "upload-cmdb":
            result = create_upload(
                client,
                name=args.name,
                description=args.description,
                records=sample_cmdb_records(),
                schema=CMDB_SCHEMA,
            )
            print(f"Uploaded CMDB context id={result.get('id')} status={result.get('status')}")
            return 0

        if args.cmd == "replace":
            if args.kind == "hr":
                result = replace_upload(client, args.upload_id, records=sample_hr_records(), schema=HR_SCHEMA)
            else:
                result = replace_upload(client, args.upload_id, records=sample_cmdb_records(), schema=CMDB_SCHEMA)
            print(f"Replaced {args.upload_id} status={result.get('status')}")
            return 0

        if args.cmd == "delete":
            delete_upload(client, args.upload_id)
            print(f"Deleted {args.upload_id}")
            return 0
    except CommandZeroError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1

    parser.error("unknown command")
    return 2


if __name__ == "__main__":
    sys.exit(main())
