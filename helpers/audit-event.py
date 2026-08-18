#!/usr/bin/env python3
"""Privileged append/read helper for the operational JSONL audit trail."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import pwd
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path


AUDIT_PATH = Path("/var/log/rdp-session-manager/audit.jsonl")
SAFE_VALUE = re.compile(r"^[A-Za-z0-9_.:@/+ -]{0,128}$")


def actor_name() -> str:
    raw_uid = os.environ.get("SUDO_UID") or os.environ.get("PKEXEC_UID")
    uid = int(raw_uid) if raw_uid and raw_uid.isdigit() else os.getuid()
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return f"uid:{uid}"


def append_event(path: Path, *, action: str, target: str, result: str,
                 error_code: str = "", plan_id: str = "", actor: str | None = None) -> dict:
    for value in (action, target, error_code, plan_id):
        if not SAFE_VALUE.fullmatch(value):
            raise ValueError("audit field contains unsupported characters")
    if result not in ("success", "failure"):
        raise ValueError("invalid audit result")
    event = {
        "schema_version": 1,
        "event_id": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor": actor or actor_name(),
        "action": action,
        "target": target,
        "result": result,
        "error_code": error_code,
        "plan_id": plan_id,
    }
    if path.parent.exists() and path.parent.is_symlink():
        raise ValueError("audit directory must not be a symlink")
    path.parent.mkdir(mode=0o750, parents=True, exist_ok=True)
    if os.geteuid() == 0:
        os.chown(path.parent, 0, 0)
        os.chmod(path.parent, 0o750)
    flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o640)
    if os.geteuid() == 0:
        os.fchown(fd, 0, 0)
    os.fchmod(fd, 0o640)
    with os.fdopen(fd, "a", encoding="utf-8") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        stream.write(json.dumps(event, separators=(",", ":")) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    return event


def read_events(path: Path) -> list[dict]:
    events = []
    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    value = json.loads(line)
                    if isinstance(value, dict):
                        events.append(value)
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        pass
    return events


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    write = subparsers.add_parser("write")
    write.add_argument("--action", required=True)
    write.add_argument("--target", default="")
    write.add_argument("--result", choices=("success", "failure"), required=True)
    write.add_argument("--error-code", default="")
    write.add_argument("--plan-id", default="")
    subparsers.add_parser("read")
    args = parser.parse_args(argv)
    if os.geteuid() != 0:
        print("Error: this helper must run as root.", file=sys.stderr)
        return 1
    try:
        if args.command == "write":
            append_event(AUDIT_PATH, action=args.action, target=args.target,
                         result=args.result, error_code=args.error_code,
                         plan_id=args.plan_id)
        else:
            print(json.dumps(read_events(AUDIT_PATH)))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
