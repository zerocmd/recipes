"""Integration health check.

Confirms the API key is valid, the service is up, and lists every
organization the application can act against. Suitable for a SOAR
pre-flight check or a cron-driven uptime probe.

Env: CMDZERO_API_KEY (required)
Run: python health_check.py
Exit code: 0 on success, 1 on auth/network failure.
"""
from __future__ import annotations

import sys

from cmdzero_client import CommandZeroClient, CommandZeroError, configure_logging


def main() -> int:
    configure_logging()
    try:
        client = CommandZeroClient()
        health = client.health()
        print(f"Health: {health.get('status', 'unknown')}")

        orgs = client.list_organizations()
        print(f"Accessible organizations: {len(orgs)}")
        for org in orgs:
            print(f"  - {org['id']}  role={org.get('role', '?'):<14}  name={org.get('name', '')}")
        return 0
    except CommandZeroError as e:
        print(f"API error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
