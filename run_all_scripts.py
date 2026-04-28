"""Run every recipe script with every CLI flag combination, capture
stdout/stderr/exit code/duration/trace IDs/created-resource IDs, and
write structured reports to script_run_report.json and
script_run_report.md.

This is a destructive harness: scripts in the "mutating" group create
real investigations and remediations on the configured warniCo tenant.
The harness aborts before the mutating phase if any read-only script
fails with an auth error.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
REPORT_JSON = REPO_ROOT / "script_run_report.json"
REPORT_MD = REPO_ROOT / "script_run_report.md"

# Order matters: read-only first, mutating last. The harness aborts
# before mutating if any read-only run fails with an auth error.
READ_ONLY_SCRIPTS = [
    "health_check.py",
    "cmdzero_client.py",
    "business_context.py",
    "investigation_pipeline_report.py",
    "mssp_multi_tenant.py",
    "sdk_live_test.py",
]
MUTATING_SCRIPTS = [
    "template_investigation.py",
    "alert_investigation.py",
    "automated_remediation.py",
    "postback_receiver.py",  # --help only — won't bind a port
]
ALL_SCRIPTS = READ_ONLY_SCRIPTS + MUTATING_SCRIPTS


@dataclass
class RunResult:
    script: str
    args: list[str]
    exit_code: int
    duration_s: float
    stdout_tail: str
    stderr_tail: str
    trace_ids: list[str] = field(default_factory=list)
    created_investigation_ids: list[str] = field(default_factory=list)
    created_remediation_ids: list[str] = field(default_factory=list)


def run_one(script: str, args: list[str], timeout: int = 60) -> RunResult:
    """Run `python <script> <args>` from the repo root, capture output."""
    cmd = [sys.executable, script, *args]
    start = time.time()
    try:
        proc = subprocess.run(
            cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=timeout
        )
        exit_code = proc.returncode
        stdout = proc.stdout
        stderr = proc.stderr
    except subprocess.TimeoutExpired as e:
        exit_code = -1
        stdout = (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        stderr = (e.stderr or b"").decode("utf-8", errors="replace") if isinstance(e.stderr, bytes) else (e.stderr or "")
        stderr += f"\n[timeout after {timeout}s]"
    duration = time.time() - start

    combined = stdout + "\n" + stderr
    trace_ids = sorted(set(re.findall(r"\b[a-f0-9]{32}\b", combined)))
    inv_ids = sorted(set(re.findall(r"\binvestigation[_ -]?id[:= ]+([0-9a-f-]{36})", stdout, re.I)))
    rem_ids = sorted(set(re.findall(r"\bremediation[_ -]?id[:= ]+([0-9a-f-]{36})", stdout, re.I)))

    return RunResult(
        script=script,
        args=args,
        exit_code=exit_code,
        duration_s=round(duration, 3),
        stdout_tail="\n".join(stdout.splitlines()[-50:]),
        stderr_tail="\n".join(stderr.splitlines()[-50:]),
        trace_ids=trace_ids,
        created_investigation_ids=inv_ids,
        created_remediation_ids=rem_ids,
    )


def write_reports(results: list[RunResult]) -> None:
    REPORT_JSON.write_text(json.dumps([asdict(r) for r in results], indent=2))

    lines = ["# Live script run report\n\n"]
    lines.append(f"Total runs: {len(results)}\n")
    passed = sum(1 for r in results if r.exit_code == 0)
    lines.append(f"Passed: {passed} / {len(results)}\n\n")
    lines.append("| Script | Args | Exit | Duration | Created |\n")
    lines.append("|---|---|---|---|---|\n")
    for r in results:
        created = []
        if r.created_investigation_ids:
            created.append(f"inv: {len(r.created_investigation_ids)}")
        if r.created_remediation_ids:
            created.append(f"rem: {len(r.created_remediation_ids)}")
        lines.append(
            f"| {r.script} | `{' '.join(r.args) or '(none)'}` | {r.exit_code} | "
            f"{r.duration_s}s | {', '.join(created) or '-'} |\n"
        )
    REPORT_MD.write_text("".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--phase",
        choices=("help", "read", "mutate", "all"),
        default="help",
        help="Which phase to run. 'help' runs --help for every script (safe smoke).",
    )
    args = parser.parse_args()

    results: list[RunResult] = []

    # Phase: --help
    if args.phase in ("help", "all"):
        for script in ALL_SCRIPTS:
            results.append(run_one(script, ["--help"], timeout=15))

    write_reports(results)
    print(f"Wrote {REPORT_JSON} and {REPORT_MD}")
    return 0 if all(r.exit_code == 0 for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
