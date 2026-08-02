#!/usr/bin/env python3
"""Privileged reversible metadata migration for one RDPSM Windows user."""

from __future__ import annotations

import argparse
import json
import os
import pwd
import shlex
import shutil
import subprocess
import time
from pathlib import Path


FILES = (
    ".rdp_profiles.json",
    ".winege_config",
    ".winege_app_path",
    ".windows_runtime.json",
    ".launch_winege_app.sh",
)


def account_home(username: str) -> Path:
    account = pwd.getpwnam(username)
    home = Path(account.pw_dir).resolve()
    if Path("/opt/rdp-users") not in home.parents:
        raise ValueError("user home is outside /opt/rdp-users")
    return home


def backup(home: Path) -> Path:
    destination = home / ".rdpsm-backups" / time.strftime("%Y%m%d-%H%M%S")
    destination.mkdir(parents=True, exist_ok=False)
    for name in FILES:
        source = home / name
        if source.exists():
            shutil.copy2(source, destination / name)
    return destination


def migrate(home: Path) -> dict:
    backup_dir = backup(home)
    try:
        umu = shutil.which("umu-run")
        if not umu:
            raise RuntimeError("umu-run must be installed before migration")
        subprocess.run([umu, "--help"], capture_output=True, check=True, timeout=15)
        profiles_path = home / ".rdp_profiles.json"
        payload = json.loads(profiles_path.read_text(encoding="utf-8"))
        profiles = payload.get("profiles", []) if isinstance(payload, dict) else payload
        if not isinstance(profiles, list):
            raise ValueError("invalid profile document")
        for profile in profiles:
            if profile.get("profile_type") != "winege-remoteapp":
                continue
            profile["runtime"] = "umu"
            profile["resource_profile"] = "windows-standard"
            if not profile.get("command_argv") and profile.get("app_command"):
                profile["command_argv"] = [
                    profile["app_command"],
                    *shlex.split(profile.get("app_args", "")),
                ]
            profile.setdefault("working_directory", "")
            profile.setdefault("environment", {})
        temporary = profiles_path.with_suffix(".json.new")
        temporary.write_text(
            json.dumps({"schema_version": 2, "profiles": profiles}, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, profiles_path)

        executable = ""
        app_path = home / ".winege_app_path"
        if app_path.exists():
            executable = app_path.read_text(encoding="utf-8").strip()
        if not executable or not Path(executable).is_file():
            raise ValueError("configured Windows executable does not exist")
        manifest = {
            "schema_version": 1,
            "runtime": "umu",
            "migration_state": "ready_for_session_validation",
            "wine_prefix": str(home / ".wine"),
            "executable": executable,
            "legacy_winege_available": (home / ".winege_config").exists(),
            "migration_backup": str(backup_dir),
        }
        (home / ".windows_runtime.json").write_text(
            json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
        )
        return {"migrated": True, "backup": str(backup_dir), "manifest": manifest}
    except Exception:
        (home / ".rdp_profiles.json.new").unlink(missing_ok=True)
        rollback(home, str(backup_dir))
        raise


def rollback(home: Path, raw_backup: str) -> dict:
    backup_dir = Path(raw_backup).resolve()
    allowed_root = (home / ".rdpsm-backups").resolve()
    if allowed_root not in backup_dir.parents or not backup_dir.is_dir():
        raise ValueError("rollback path is outside this user's backup directory")
    for name in FILES:
        source = backup_dir / name
        target = home / name
        if source.exists():
            shutil.copy2(source, target)
        elif target.exists() and name == ".windows_runtime.json":
            target.unlink()
    return {"rolled_back": True, "backup": str(backup_dir)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("--rollback", default="")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("root privileges are required")
    account = pwd.getpwnam(args.username)
    home = account_home(args.username)
    result = rollback(home, args.rollback) if args.rollback else migrate(home)
    for path in (home / ".rdp_profiles.json", home / ".windows_runtime.json"):
        if path.exists():
            shutil.chown(path, user=account.pw_uid, group=account.pw_gid)
    backups = home / ".rdpsm-backups"
    if backups.exists():
        for path in (backups, *backups.rglob("*")):
            shutil.chown(path, user=account.pw_uid, group=account.pw_gid)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
