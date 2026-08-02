#!/usr/bin/env python3
"""Safe xrdp session dispatcher and single-application supervisor."""

from __future__ import annotations

import json
import os
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


PROFILE_FILE = ".rdp_profiles.json"


def audit(event: str, **fields: Any) -> None:
    record = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "component": "rdpsm-session",
        "event": event,
        "username": os.environ.get("USER", "unknown"),
        **fields,
    }
    print(json.dumps(record, sort_keys=True), file=sys.stderr, flush=True)


def load_profiles(home: Path) -> list[dict[str, Any]]:
    payload = json.loads((home / PROFILE_FILE).read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        if payload.get("schema_version") not in (None, 2):
            raise ValueError("unsupported profile schema")
        profiles = payload.get("profiles", [])
    else:
        profiles = payload
    if not isinstance(profiles, list) or not profiles:
        raise ValueError("no connection profiles configured")
    return profiles


def command_argv(profile: dict[str, Any]) -> list[str]:
    argv = profile.get("command_argv")
    if isinstance(argv, list) and argv and all(isinstance(item, str) and item for item in argv):
        return argv
    command = profile.get("app_command", "")
    if not isinstance(command, str) or not command:
        return []
    arguments = profile.get("app_args", "")
    return [command] + shlex.split(arguments)


def select_profile(profiles: list[dict[str, Any]], requested: str = "") -> dict[str, Any]:
    if requested:
        for profile in profiles:
            if requested in (profile.get("profile_id"), profile.get("name")):
                return profile
        raise ValueError(f"unknown profile: {requested}")
    defaults = [profile for profile in profiles if profile.get("is_default")]
    if len(profiles) == 1 or defaults:
        return (defaults or profiles)[0]

    chooser = Path("/opt/rdp-users/rdp-session-launcher.py")
    if not chooser.exists():
        raise ValueError("multiple profiles require the graphical chooser")
    wm = subprocess.Popen(["openbox"], start_new_session=True)
    try:
        result = subprocess.run(
            [sys.executable, str(chooser)],
            capture_output=True,
            text=True,
            timeout=3600,
            check=True,
        )
    finally:
        terminate_group(wm, grace=2)
    selected = json.loads(result.stdout)
    if selected.get("profile_id") not in {item.get("profile_id") for item in profiles}:
        raise ValueError("chooser returned an unknown profile")
    return selected


def desktop_argv(profile: dict[str, Any]) -> list[str]:
    desktop = profile.get("desktop_env", "xfce")
    if desktop == "gnome":
        return ["gnome-session", "--session=gnome-flashback-metacity"]
    if desktop == "kde":
        return ["startplasma-x11"]
    return ["startxfce4"]


def write_openbox_config(home: Path) -> Path:
    directory = home / ".config" / "openbox"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "rdpsm-remoteapp.xml"
    path.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<openbox_config xmlns="http://openbox.org/3.4/rc">
  <applications><application class="*"><maximized>yes</maximized><decor>yes</decor></application></applications>
</openbox_config>
""",
        encoding="utf-8",
    )
    return path


def runtime_argv(profile: dict[str, Any], home: Path) -> list[str]:
    app = command_argv(profile)
    if profile.get("profile_type") != "winege-remoteapp":
        return app
    if not app:
        app_path = home / ".winege_app_path"
        if app_path.exists():
            app = [app_path.read_text(encoding="utf-8").strip()]
    elif profile.get("profile_id") == "default":
        app_path = home / ".winege_app_path"
        if app_path.exists():
            app[0] = app_path.read_text(encoding="utf-8").strip()
    if not app:
        raise ValueError("Windows application path is missing")

    runtime = profile.get("runtime", "umu")
    if runtime == "umu":
        umu = shutil.which("umu-run")
        if umu:
            return [umu, app[0], *app[1:]]
        legacy = home / ".launch_winege_app.sh"
        if not legacy.exists():
            raise RuntimeError("umu-run is unavailable and no legacy WineGE runtime exists")
    legacy = home / ".launch_winege_app.sh"
    if legacy.exists():
        return [str(legacy), *app[1:]]
    wine = shutil.which("wine")
    if not wine:
        raise RuntimeError("no Windows runtime is available")
    return [wine, *app]


def terminate_group(process: subprocess.Popen, grace: float = 5.0) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()
    except ProcessLookupError:
        pass


def mark_runtime_validated(home: Path) -> None:
    path = home / ".windows_runtime.json"
    if not path.exists():
        return
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["migration_state"] = "validated"
        payload["validated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        temporary = path.with_suffix(".json.new")
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, path)
    except (OSError, ValueError, TypeError):
        audit("runtime_validation_metadata_failed")


def run_remoteapp(profile: dict[str, Any], home: Path) -> int:
    environment = os.environ.copy()
    custom_environment = profile.get("environment", {})
    if not isinstance(custom_environment, dict):
        raise ValueError("profile environment must be an object")
    for key, value in custom_environment.items():
        if not isinstance(key, str) or not isinstance(value, str) or "\x00" in key + value:
            raise ValueError("invalid environment entry")
        environment[key] = value
    environment.update(
        {
            "HOME": str(home),
            "WINEDEBUG": environment.get("WINEDEBUG", "-all"),
            "WINEPREFIX": environment.get("WINEPREFIX", str(home / ".wine")),
        }
    )
    shared_runtime_root = Path("/opt/rdp-session-manager/runtimes")
    if profile.get("profile_type") == "winege-remoteapp" and shared_runtime_root.is_dir():
        environment.setdefault("XDG_DATA_HOME", str(shared_runtime_root))
        environment.setdefault("PROTONPATH", "UMU-Proton")
        environment.setdefault("GAMEID", "umu-default")
        environment.setdefault("STORE", "none")
    cwd = Path(profile.get("working_directory") or home)
    if not cwd.is_dir():
        raise ValueError(f"working directory does not exist: {cwd}")

    wm = subprocess.Popen(
        ["openbox", "--config-file", str(write_openbox_config(home))],
        start_new_session=True,
        env=environment,
    )
    app = None
    try:
        time.sleep(0.2)
        argv = runtime_argv(profile, home)
        if not argv:
            raise ValueError("application command is empty")
        audit(
            "application_start",
            profile_id=profile.get("profile_id", ""),
            profile_type=profile.get("profile_type", ""),
            executable=Path(argv[0]).name,
        )
        app = subprocess.Popen(argv, cwd=str(cwd), env=environment, start_new_session=True)
        return_code = app.wait()
        audit(
            "application_exit",
            profile_id=profile.get("profile_id", ""),
            return_code=return_code,
        )
        if return_code == 0 and profile.get("profile_type") == "winege-remoteapp":
            mark_runtime_validated(home)
        return return_code
    finally:
        if app is not None:
            terminate_group(app)
        terminate_group(wm, grace=2)
        if profile.get("profile_type") == "winege-remoteapp":
            wineserver = shutil.which("wineserver")
            if wineserver:
                subprocess.run([wineserver, "-k"], env=environment, timeout=10, check=False)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    home = Path(os.environ.get("HOME", "")).resolve()
    if not home.is_dir():
        print("invalid HOME", file=sys.stderr)
        return 2
    try:
        profile = select_profile(load_profiles(home), arguments[0] if arguments else "")
        if profile.get("profile_type", "desktop") == "desktop":
            os.execvp(desktop_argv(profile)[0], desktop_argv(profile))
        return run_remoteapp(profile, home)
    except Exception as exc:
        audit("session_error", error_type=type(exc).__name__, message=str(exc))
        print(f"RDPSM session failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
