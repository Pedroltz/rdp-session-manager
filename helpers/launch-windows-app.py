#!/usr/bin/env python3
"""Launch one RDPSM Windows application without shell interpolation."""

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

for candidate in (
    Path("/usr/share/rdp-session-manager/src"),
    Path(__file__).resolve().parents[1] / "src",
):
    if candidate.is_dir():
        sys.path.insert(0, str(candidate))

from core.windows_app import WindowsAppError, WindowsAppManager  # noqa: E402


def window_ids():
    xdotool = shutil.which("xdotool")
    if not xdotool:
        return None
    result = subprocess.run(
        [xdotool, "search", "--all", "--name", "."],
        capture_output=True,
        text=True,
    )
    if result.returncode not in (0, 1):
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def run_process(command, environment, log_path):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    windows_before = window_ids()
    with log_path.open("a", encoding="utf-8", errors="replace") as log:
        process = subprocess.Popen(command, env=environment, stdout=log, stderr=log)
        for _ in range(30):
            if process.poll() is not None:
                break
            windows_after = window_ids()
            if windows_before is None or (
                windows_after is not None and windows_after - windows_before
            ):
                return process, True
            time.sleep(0.5)
        return process, windows_before is None and process.poll() is None


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: launch-windows-app.py APP_ID [APP_ARGS...]", file=sys.stderr)
        return 2
    app_id = sys.argv[1]
    manager = WindowsAppManager(Path.home())
    try:
        state = manager.load_state(app_id)
        if state["state"] == "awaiting_assisted_install":
            manifest = manager.load_manifest(app_id)
            command = manager.resolve_runner(manifest) + [state["installer"]]
            process, _ = run_process(
                command,
                manager.runner_environment(manifest),
                manager.app_dir(app_id) / "logs" / "assisted-install.log",
            )
            exit_code = process.wait()
            if exit_code not in manifest["recipe"]["installer"]["success_codes"]:
                manager.set_state(
                    app_id, "failed", f"Interactive installer exited with code {exit_code}"
                )
                return exit_code or 1
            state = manager.finalize_assisted(app_id)
            if state["state"] == "selection_required":
                return 3

        command, environment = manager.launch_command(app_id, sys.argv[2:])
        process, ready = run_process(
            command,
            environment,
            manager.app_dir(app_id) / "logs" / "launch.log",
        )
        if not ready:
            manager.set_state(app_id, "failed", "Application exited before opening a window")
            return process.wait() or 1
        manager.mark_rdp_ready(app_id, process.pid)
        return process.wait()
    except (OSError, ValueError, WindowsAppError) as exc:
        print(f"Windows application launch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
