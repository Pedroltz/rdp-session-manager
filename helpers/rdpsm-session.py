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
    if len(profiles) == 1:
        return profiles[0]

    chooser = Path("/opt/rdp-users/rdp-session-launcher.py")
    if not chooser.exists():
        defaults = [profile for profile in profiles if profile.get("is_default")]
        return (defaults or profiles)[0]
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


def umu_runtime_ready(root: Path) -> bool:
    runtime = root / "umu" / "steamrt3"
    proton_root = root / "Steam" / "compatibilitytools.d"
    return (
        (runtime / ".installed.ok").is_file()
        and any(path.is_dir() for path in runtime.glob("sniper_platform_*"))
        and any(proton_root.glob("*/toolmanifest.vdf"))
    )


def configured_runtime(profile: dict[str, Any], home: Path) -> str:
    """Prefer the provisioner's per-user fallback over the requested runtime."""
    runtime = profile.get("runtime", "umu")
    manifest = home / ".windows_runtime.json"
    try:
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        configured = payload.get("runtime")
        if configured in {"umu", "wine"}:
            runtime = configured
    except (OSError, ValueError, TypeError):
        pass
    return runtime


def installed_executables(prefix: Path) -> dict[str, tuple[int, int]]:
    """Return executable path -> (mtime_ns, size) for application directories."""
    inventory: dict[str, tuple[int, int]] = {}
    drive_c = prefix / "drive_c"
    for root_name in ("Program Files", "Program Files (x86)"):
        root = drive_c / root_name
        if not root.is_dir():
            continue
        for executable in root.rglob("*.exe"):
            try:
                stat = executable.stat()
            except OSError:
                continue
            inventory[str(executable)] = (stat.st_mtime_ns, stat.st_size)
    return inventory


def _is_application_executable(path: Path) -> bool:
    lowered = str(path).lower().replace("\\", "/")
    name = path.name.lower()
    ignored_names = (
        "unins",
        "uninst",
        "setup",
        "install",
        "update",
        "gup.exe",
        "crashreport",
        "helper",
        "vc_redist",
        "dxsetup",
    )
    ignored_paths = (
        "/common files/",
        "/internet explorer/",
        "/windows media player/",
        "/windows nt/",
    )
    return not (
        any(token in name for token in ignored_names)
        or any(token in lowered for token in ignored_paths)
    )


def promote_installed_executable(
    home: Path,
    prefix: Path,
    before: dict[str, tuple[int, int]],
    profile_id: str = "",
    allow_existing: bool = False,
) -> Path | None:
    """Select the most likely application created or changed by an installer."""
    changed = []
    for raw_path, metadata in installed_executables(prefix).items():
        path = Path(raw_path)
        if not _is_application_executable(path):
            continue
        if not allow_existing and before.get(raw_path) == metadata:
            continue
        # Prefer a sizeable, top-level executable in Program Files. The
        # ordering remains deterministic when two candidates score equally.
        relative_depth = len(path.relative_to(prefix / "drive_c").parts)
        score = metadata[1] - (relative_depth * 1024)
        changed.append((score, raw_path.lower(), path))
    if not changed:
        return None

    changed.sort(key=lambda item: (-item[0], item[1]))
    selected = changed[0][2]
    app_path = home / ".winege_app_path"
    temporary = app_path.with_name(f"{app_path.name}.new")
    temporary.write_text(f"{selected}\n", encoding="utf-8")
    os.replace(temporary, app_path)

    manifest_path = home / ".windows_runtime.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["executable"] = str(selected)
        temporary_manifest = manifest_path.with_name(f"{manifest_path.name}.new")
        temporary_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_manifest, manifest_path)
    except (OSError, ValueError, TypeError):
        audit("installed_executable_manifest_update_failed")

    profiles_path = home / PROFILE_FILE
    try:
        document = json.loads(profiles_path.read_text(encoding="utf-8"))
        profiles = document.get("profiles", []) if isinstance(document, dict) else document
        for item in profiles:
            if not isinstance(item, dict):
                continue
            if profile_id and item.get("profile_id") != profile_id:
                continue
            if not profile_id and not item.get("is_default"):
                continue
            item["app_command"] = str(selected)
            old_argv = item.get("command_argv", [])
            item["command_argv"] = [str(selected), *old_argv[1:]] if old_argv else [str(selected)]
            break
        temporary_profiles = profiles_path.with_name(f"{profiles_path.name}.new")
        temporary_profiles.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_profiles, profiles_path)
    except (OSError, ValueError, TypeError):
        audit("installed_executable_profile_update_failed")
    audit("installed_executable_selected", executable=str(selected))
    return selected


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

    runtime = configured_runtime(profile, home)
    legacy = home / ".launch_winege_app.sh"
    if runtime == "umu":
        umu = shutil.which("umu-run")
        if umu:
            shared_root = Path("/opt/rdp-session-manager/runtimes")
            if shared_root.is_dir() and not umu_runtime_ready(shared_root):
                raise RuntimeError(
                    "The shared UMU runtime is incomplete. "
                    "Run 'rdpsm user repair USERNAME' before reconnecting."
                )
            return [umu, app[0], *app[1:]]
        if not legacy.exists():
            raise RuntimeError("umu-run is unavailable and no legacy WineGE runtime exists")
        return [str(legacy), *app[1:]]

    if runtime == "wine":
        wine = shutil.which("wine")
        if wine:
            # The compatibility wrapper may still contain the original
            # installer path. The profile/.winege_app_path is authoritative.
            return [wine, *app]
        if legacy.exists():
            return [str(legacy), *app[1:]]
        raise RuntimeError("system Wine is unavailable")

    if legacy.exists():
        return [str(legacy), *app[1:]]
    raise RuntimeError(f"unsupported Windows runtime: {runtime}")


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
        environment.setdefault("UMU_RUNTIME_UPDATE", "0")
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
        prefix = Path(environment["WINEPREFIX"])
        before_install = (
            installed_executables(prefix)
            if profile.get("profile_type") == "winege-remoteapp"
            else {}
        )
        selected_app = command_argv(profile)
        if profile.get("profile_id") == "default":
            app_path = home / ".winege_app_path"
            if app_path.exists():
                selected_app = [app_path.read_text(encoding="utf-8").strip()]
        selected_is_installer = bool(
            selected_app and not _is_application_executable(Path(selected_app[0]))
        )
        app = subprocess.Popen(argv, cwd=str(cwd), env=environment, start_new_session=True)
        return_code = app.wait()
        if return_code == 0 and profile.get("profile_type") == "winege-remoteapp":
            selected = promote_installed_executable(
                home,
                prefix,
                before_install,
                str(profile.get("profile_id", "")),
                allow_existing=selected_is_installer,
            )
            if selected is not None:
                # Keep the current RDP connection useful: replace the completed
                # installer with the application that was just installed.
                promoted_profile = dict(profile)
                original_app = command_argv(profile)
                promoted_profile["command_argv"] = [
                    str(selected),
                    *original_app[1:],
                ]
                promoted_profile["app_command"] = str(selected)
                argv = runtime_argv(promoted_profile, home)
                audit(
                    "installed_application_start",
                    profile_id=profile.get("profile_id", ""),
                    executable=str(selected),
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
        zenity = shutil.which("zenity")
        if zenity and os.environ.get("DISPLAY"):
            subprocess.run(
                [
                    zenity,
                    "--error",
                    "--title=RDP Session Manager",
                    f"--text={exc}",
                ],
                timeout=30,
                check=False,
            )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
