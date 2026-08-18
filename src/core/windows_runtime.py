#!/usr/bin/env python3
"""Inventory and reversible profile migration from legacy WineGE to umu."""

from __future__ import annotations

import json
import os
import pwd
import subprocess
import sys
from pathlib import Path

from utils.polkit import get_privilege_command
from core.audit import audited_command


class WindowsRuntimeMigrator:
    def __init__(self, users_home: str | Path = "/opt/rdp-users", helper_path=None):
        self.users_home = Path(users_home)
        local = Path(__file__).resolve().parents[2] / "helpers" / "migrate-windows-runtime.py"
        installed = Path("/usr/share/rdp-session-manager/helpers/migrate-windows-runtime.py")
        self.helper_path = Path(helper_path) if helper_path else (local if local.exists() else installed)

    def inventory(self, username: str | None = None) -> list[dict]:
        accounts = []
        for account in pwd.getpwall():
            if username and account.pw_name != username:
                continue
            home = Path(account.pw_dir)
            if self.users_home not in home.parents:
                continue
            profiles = home / ".rdp_profiles.json"
            legacy = home / ".winege_config"
            manifest = home / ".windows_runtime.json"
            if profiles.exists() or legacy.exists() or manifest.exists():
                accounts.append({
                    "username": account.pw_name,
                    "home": str(home),
                    "legacy_winege": legacy.exists(),
                    "runtime_manifest": manifest.exists(),
                    "profile_schema": self._schema(profiles),
                    "migratable": legacy.exists() or self._schema(profiles) < 2,
                })
        return accounts

    @staticmethod
    def _schema(path: Path) -> int:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            return int(payload.get("schema_version", 1)) if isinstance(payload, dict) else 1
        except (OSError, ValueError, TypeError):
            return 0

    def migrate(self, username: str, rollback: str = "") -> dict:
        privilege = [] if os.geteuid() == 0 else get_privilege_command()[1]
        action = "windows.runtime.rollback" if rollback else "windows.runtime.migrate"
        command = audited_command(
            privilege,
            action,
            username,
            [sys.executable, str(self.helper_path), username],
        )
        if rollback:
            command += ["--rollback", rollback]
        result = subprocess.run(command, capture_output=True, text=True, timeout=60)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        return json.loads(result.stdout)
