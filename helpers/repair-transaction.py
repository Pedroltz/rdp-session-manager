#!/usr/bin/env python3
"""Create and restore snapshots of files managed by user repair."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


MANAGED_FILES = (
    ".xsession",
    ".xinitrc",
    ".rdp_profiles.json",
    ".winege_config",
    ".winege_app_path",
    ".launch_winege_app.sh",
    ".windows_runtime.json",
)


def _copy_entry(source: Path, destination: Path) -> None:
    metadata = source.lstat()
    if source.is_symlink():
        destination.symlink_to(os.readlink(source))
    else:
        shutil.copy2(source, destination, follow_symlinks=False)
    if os.geteuid() == 0:
        os.chown(
            destination,
            metadata.st_uid,
            metadata.st_gid,
            follow_symlinks=False,
        )


def create_snapshot(home: Path, backup_root: Path | None = None) -> Path:
    """Snapshot managed entries and record which ones did not exist."""
    home = home.resolve()
    root = backup_root or home / ".rdpsm-backups"
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    snapshot = root / f"repair-{timestamp}-{os.getpid()}"
    snapshot.mkdir(mode=0o700)

    present = []
    for name in MANAGED_FILES:
        source = home / name
        if source.exists() or source.is_symlink():
            _copy_entry(source, snapshot / name)
            present.append(name)

    manifest = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "home": str(home),
        "home_mode": home.stat().st_mode & 0o7777,
        "home_uid": home.stat().st_uid,
        "home_gid": home.stat().st_gid,
        "managed_files": list(MANAGED_FILES),
        "present": present,
    }
    manifest_path = snapshot / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    return snapshot


def restore_snapshot(snapshot: Path, home: Path) -> None:
    """Restore a snapshot, including removing entries absent before repair."""
    snapshot = snapshot.resolve()
    home = home.resolve()
    manifest = json.loads((snapshot / "manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema_version") != 1 or manifest.get("home") != str(home):
        raise ValueError("snapshot does not belong to this home directory")
    managed = manifest.get("managed_files")
    present = set(manifest.get("present", []))
    if managed != list(MANAGED_FILES) or not present.issubset(MANAGED_FILES):
        raise ValueError("invalid repair snapshot manifest")

    for name in MANAGED_FILES:
        target = home / name
        if target.is_dir() and not target.is_symlink():
            raise ValueError(f"refusing to replace directory: {target}")
        if target.exists() or target.is_symlink():
            target.unlink()
        if name in present:
            _copy_entry(snapshot / name, target)
    os.chmod(home, int(manifest["home_mode"]))
    if os.geteuid() == 0:
        os.chown(home, int(manifest["home_uid"]), int(manifest["home_gid"]))


def _validate_privileged_paths(home: Path, username: str, snapshot: Path | None = None) -> None:
    if os.geteuid() != 0:
        raise PermissionError("this helper must run as root")
    expected = Path("/opt/rdp-users") / username
    if home != expected:
        raise ValueError("refusing a home outside /opt/rdp-users")
    expected_backup = Path("/var/lib/rdp-session-manager/backups") / username
    if snapshot is not None and snapshot.parent != expected_backup:
        raise ValueError("snapshot is outside the managed backup directory")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup = subparsers.add_parser("backup")
    backup.add_argument("home", type=Path)
    backup.add_argument("username")
    restore = subparsers.add_parser("restore")
    restore.add_argument("snapshot", type=Path)
    restore.add_argument("home", type=Path)
    restore.add_argument("username")
    args = parser.parse_args(argv)
    try:
        if args.command == "backup":
            _validate_privileged_paths(args.home, args.username)
            backup_root = Path("/var/lib/rdp-session-manager/backups") / args.username
            if backup_root.exists() and backup_root.is_symlink():
                raise ValueError("managed backup directory must not be a symlink")
            backup_root.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chown(backup_root, 0, 0)
            os.chmod(backup_root, 0o700)
            snapshot = create_snapshot(args.home, backup_root)
            print(snapshot)
        else:
            _validate_privileged_paths(args.home, args.username, args.snapshot)
            restore_snapshot(args.snapshot, args.home)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
