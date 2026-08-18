#!/usr/bin/env python3
"""Run one privileged command and audit its result without logging argv/stdin."""

from __future__ import annotations

import argparse
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def _audit_module():
    path = Path(__file__).with_name("audit-event.py")
    spec = importlib.util.spec_from_file_location("rdpsm_audit_event", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--target", default="system")
    parser.add_argument("--success-code", action="append", type=int, default=[])
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if os.geteuid() != 0:
        print("Error: audit-exec must run as root.", file=sys.stderr)
        return 1
    if not command:
        print("Error: no command was provided.", file=sys.stderr)
        return 2

    error_code = ""
    try:
        completed = subprocess.run(command, check=False)
        status = completed.returncode
        if status < 0:
            status = 128 + abs(status)
        successful_codes = {0, *args.success_code}
        if status not in successful_codes:
            error_code = f"exit-{status}"
    except OSError:
        status = 127
        error_code = "execution-error"

    try:
        audit = _audit_module()
        audit.append_event(
            audit.AUDIT_PATH,
            action=args.action,
            target=args.target,
            result="success" if status in successful_codes else "failure",
            error_code=error_code,
        )
    except Exception as exc:
        print(f"Warning: could not write the privileged audit event: {exc}", file=sys.stderr)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
