#!/usr/bin/env python3
"""Apply the configured cgroup slice to one RDPSM user."""

from __future__ import annotations

import configparser
import json
import os
import pwd
import subprocess
import sys
from pathlib import Path


DEFAULTS = {
    "linux-light": {
        "memory_high_mb": 768,
        "memory_max_mb": 1280,
        "cpu_quota_percent": 100,
        "tasks_max": 256,
    },
    "windows-standard": {
        "memory_high_mb": 1536,
        "memory_max_mb": 2560,
        "cpu_quota_percent": 150,
        "tasks_max": 512,
    },
}


def detect_profile(home: Path) -> str:
    path = home / ".rdp_profiles.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        profiles = payload.get("profiles", []) if isinstance(payload, dict) else payload
        if any(item.get("profile_type") == "winege-remoteapp" for item in profiles):
            return "windows-standard"
    except (OSError, ValueError, TypeError):
        pass
    return "linux-light"


def main() -> int:
    if os.geteuid() != 0 or len(sys.argv) not in (2, 3):
        print("usage: apply-user-resource.py USERNAME [PROFILE]", file=sys.stderr)
        return 2
    account = pwd.getpwnam(sys.argv[1])
    if account.pw_uid < 1000 or Path("/opt/rdp-users") not in Path(account.pw_dir).resolve().parents:
        raise ValueError("refusing limits for a non-RDPSM system user")
    config_path = Path("/etc/rdp-session-manager/server.ini")
    if not config_path.exists():
        return 0
    profile_name = sys.argv[2] if len(sys.argv) == 3 else detect_profile(Path(account.pw_dir))
    if profile_name not in DEFAULTS:
        raise ValueError(f"unknown resource profile: {profile_name}")
    values = dict(DEFAULTS[profile_name])
    parser = configparser.ConfigParser()
    parser.read(config_path)
    section = f"resource:{profile_name}"
    if parser.has_section(section):
        for key in values:
            candidate = parser.getint(section, key, fallback=values[key])
            if candidate > 0:
                values[key] = candidate
    dropin = (
        Path("/etc/systemd/system")
        / f"user-{account.pw_uid}.slice.d"
        / "50-rdpsm.conf"
    )
    dropin.parent.mkdir(parents=True, exist_ok=True)
    temporary = dropin.with_suffix(".new")
    temporary.write_text(
        "[Slice]\n"
        f"MemoryHigh={values['memory_high_mb']}M\n"
        f"MemoryMax={values['memory_max_mb']}M\n"
        f"CPUQuota={values['cpu_quota_percent']}%\n"
        f"TasksMax={values['tasks_max']}\n",
        encoding="utf-8",
    )
    os.replace(temporary, dropin)
    subprocess.run(["systemctl", "daemon-reload"], check=True, timeout=30)
    print(f"Applied {profile_name} limits to {account.pw_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
