#!/usr/bin/env python3
"""Read and export the privileged operational audit trail."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from utils.polkit import get_privilege_command


class AuditStore:
    def __init__(
        self,
        audit_path: Path | str = "/var/log/rdp-session-manager/audit.jsonl",
        helper_path: Path | str | None = None,
        runner: Callable = subprocess.run,
    ):
        self.audit_path = Path(audit_path)
        if helper_path is None:
            local = Path(__file__).parent.parent.parent / "helpers" / "audit-event.py"
            installed = Path("/usr/share/rdp-session-manager/helpers/audit-event.py")
            helper_path = local if local.exists() else installed
        self.helper_path = Path(helper_path)
        self.runner = runner

    def _load(self) -> list[dict]:
        try:
            with self.audit_path.open(encoding="utf-8") as stream:
                return self._parse_lines(stream)
        except FileNotFoundError:
            return []
        except PermissionError:
            _, privilege = get_privilege_command()
            completed = self.runner(
                privilege + [str(self.helper_path), "read"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if completed.returncode != 0:
                raise RuntimeError(completed.stderr.strip() or "could not read audit log")
            data = json.loads(completed.stdout or "[]")
            return [item for item in data if isinstance(item, dict)]

    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> list[dict]:
        events = []
        for line in lines:
            try:
                event = json.loads(line)
                if isinstance(event, dict):
                    events.append(event)
            except json.JSONDecodeError:
                continue
        return events

    @staticmethod
    def _timestamp(value: str) -> datetime:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    def list_events(
        self,
        *,
        limit: int = 100,
        user: str = "",
        action: str = "",
        result: str = "",
        since: str = "",
        until: str = "",
    ) -> list[dict]:
        if limit < 1:
            raise ValueError("limit must be at least 1")
        since_at = self._timestamp(since) if since else None
        until_at = self._timestamp(until) if until else None
        selected = []
        for event in self._load():
            if user and user not in (event.get("actor"), event.get("target")):
                continue
            if action and event.get("action") != action:
                continue
            if result and event.get("result") != result:
                continue
            try:
                occurred_at = self._timestamp(str(event.get("timestamp", "")))
            except (TypeError, ValueError):
                continue
            if since_at and occurred_at < since_at:
                continue
            if until_at and occurred_at > until_at:
                continue
            selected.append(event)
        return selected[-limit:]

    def export(self, output: Path | str, **filters) -> tuple[Path, int]:
        destination = Path(output).expanduser()
        events = self.list_events(**filters)
        flags = os.O_CREAT | os.O_TRUNC | os.O_WRONLY
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(destination, flags, 0o600)
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event, separators=(",", ":")) + "\n")
        return destination, len(events)

    def record_privileged(self, *, action: str, target: str, success: bool,
                          error_code: str = "", plan_id: str = "") -> None:
        """Record from an already privileged controller process."""
        if os.geteuid() != 0:
            raise PermissionError("privileged audit recording requires root")
        completed = self.runner(
            [
                str(self.helper_path),
                "write",
                "--action", action,
                "--target", target,
                "--result", "success" if success else "failure",
                "--error-code", error_code,
                "--plan-id", plan_id,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if completed.returncode:
            raise RuntimeError(completed.stderr.strip() or "could not write audit event")


def audited_command(privilege: list[str], action: str, target: str,
                    command: list[str], success_codes=(0,)) -> list[str]:
    """Build a privileged command whose child result is audited safely."""
    local = Path(__file__).parent.parent.parent / "helpers" / "audit-exec.py"
    installed = Path("/usr/share/rdp-session-manager/helpers/audit-exec.py")
    helper = local if local.exists() else installed
    audit_options = [
        *privilege,
        str(helper),
        "--action", action,
        "--target", target,
    ]
    for code in success_codes:
        if code != 0:
            audit_options.extend(("--success-code", str(code)))
    return [*audit_options, "--", *command]
