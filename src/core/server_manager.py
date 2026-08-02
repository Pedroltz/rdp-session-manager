#!/usr/bin/env python3
"""Planning, diagnostics, capacity checks, and application of server profiles."""

from __future__ import annotations

import json
import ipaddress
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable, Iterable, Optional

import psutil

from core.server_config import RESOURCE_PROFILES, ServerConfig, ServerSettings
from utils.polkit import get_privilege_command


class ServerManager:
    SUPPORTED = {
        "ubuntu": ("22.04", "24.04"),
        "debian": ("12", "13"),
    }

    def __init__(
        self,
        config_path: str | Path = "/etc/rdp-session-manager/server.ini",
        xrdp_ini: str | Path = "/etc/xrdp/xrdp.ini",
        sesman_ini: str | Path = "/etc/xrdp/sesman.ini",
        helper_path: str | Path | None = None,
        command_runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ):
        self.config = ServerConfig(config_path)
        self.xrdp_ini = Path(xrdp_ini)
        self.sesman_ini = Path(sesman_ini)
        self.command_runner = command_runner
        if helper_path:
            self.helper_path = Path(helper_path)
        else:
            local = Path(__file__).resolve().parents[2] / "helpers" / "apply-server-profile.py"
            installed = Path("/usr/share/rdp-session-manager/helpers/apply-server-profile.py")
            self.helper_path = local if local.exists() else installed

    @staticmethod
    def _os_release(path: Path = Path("/etc/os-release")) -> dict[str, str]:
        values = {}
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    values[key] = value.strip().strip("\"'")
        except OSError:
            pass
        return values

    def preflight(self) -> dict:
        settings = self.config.load()
        release = self._os_release()
        distro = release.get("ID", "unknown")
        version = release.get("VERSION_ID", "unknown")
        cgroup_v2 = Path("/sys/fs/cgroup/cgroup.controllers").exists()
        commands = {
            name: bool(shutil.which(name))
            for name in ("xrdp", "xrdp-sesman", "systemctl", "loginctl", "openbox", "dbus-launch")
        }
        xrdp_version = "unknown"
        gfx_supported = False
        if commands.get("xrdp"):
            try:
                version_result = self.command_runner(
                    ["xrdp", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                version_text = f"{version_result.stdout}\n{version_result.stderr}"
                match = re.search(r"\b(\d+\.\d+(?:\.\d+)?)\b", version_text)
                if match:
                    xrdp_version = match.group(1)
                    major, minor, *_ = [int(item) for item in xrdp_version.split(".")]
                    gfx_supported = (major, minor) >= (0, 10)
            except (OSError, subprocess.SubprocessError):
                pass
        errors = settings.validate()
        warnings = []
        supported = distro in self.SUPPORTED and any(
            version.startswith(candidate) for candidate in self.SUPPORTED.get(distro, ())
        )
        if not supported:
            warnings.append(f"{distro} {version} is not in the production support matrix")
        if not cgroup_v2:
            errors.append("cgroup v2 is required for resource enforcement")
        missing = [name for name, present in commands.items() if not present]
        if missing:
            errors.append("missing commands: " + ", ".join(missing))
        if not self.xrdp_ini.exists() or not self.sesman_ini.exists():
            errors.append("xrdp.ini and sesman.ini must exist")
        if not Path(settings.tls_certificate).is_file():
            errors.append(f"TLS certificate not found: {settings.tls_certificate}")
        if not Path(settings.tls_key).is_file():
            errors.append(f"TLS key not found: {settings.tls_key}")
        if settings.network_mode == "private" and not settings.allowed_network:
            warnings.append("allowed_network is unset; firewall changes will not be made")
        if settings.allowed_network and not shutil.which("nft"):
            errors.append("nft is required when allowed_network is configured")

        capacity = self.capacity(
            ['linux-light'] * settings.linux_session_slots
            + ['windows-standard'] * settings.windows_session_slots,
            settings=settings,
        )
        if not capacity["admissible"]:
            errors.append("configured session mix exceeds safe host memory capacity")
        return {
            "ready": not errors,
            "supported": supported,
            "distribution": distro,
            "version": version,
            "architecture": platform.machine(),
            "cgroup_v2": cgroup_v2,
            "commands": commands,
            "xrdp_version": xrdp_version,
            "gfx_supported": gfx_supported,
            "settings": settings.to_dict(),
            "errors": errors,
            "warnings": warnings,
            "capacity": capacity,
        }

    def capacity(
        self,
        resource_profiles: Iterable[str],
        settings: Optional[ServerSettings] = None,
    ) -> dict:
        requested = list(resource_profiles)
        configured_profiles = self.config.load_resource_profiles()
        unknown = sorted(set(requested) - set(configured_profiles))
        total_mb = sum(
            configured_profiles[name]["memory_max_mb"]
            for name in requested
            if name in configured_profiles
        )
        total_system_mb = int(psutil.virtual_memory().total / (1024 * 1024))
        reserve = (settings or self.config.load()).memory_reserve_percent
        safe_mb = int(total_system_mb * (100 - reserve) / 100)
        return {
            "admissible": not unknown and total_mb <= safe_mb,
            "requested_sessions": len(requested),
            "requested_memory_max_mb": total_mb,
            "safe_memory_mb": safe_mb,
            "system_memory_mb": total_system_mb,
            "reserve_percent": reserve,
            "unknown_profiles": unknown,
        }

    def plan(self) -> dict:
        settings = self.config.load()
        resource_profiles = self.config.load_resource_profiles()
        capacity = self.capacity(
            ['linux-light'] * settings.linux_session_slots
            + ['windows-standard'] * settings.windows_session_slots,
            settings=settings,
        )
        return {
            "settings": settings.to_dict(),
            "resource_profiles": resource_profiles,
            "capacity": capacity,
            "changes": [
                {"file": str(self.config.path), "purpose": "system-wide RDPSM settings"},
                {"file": str(self.xrdp_ini), "purpose": "TLS, transport and color-depth tuning"},
                {"file": str(self.sesman_ini), "purpose": "session limits and lifecycle"},
                {
                    "file": "/etc/systemd/system/user-<uid>.slice.d/50-rdpsm.conf",
                    "purpose": "per-user resource limits",
                },
            ],
            "restart_services": ["xrdp", "xrdp-sesman"],
            "backup": "/var/backups/rdp-session-manager/<timestamp>",
            "firewall": (
                f"restrict TCP/3389 to {settings.allowed_network}"
                if settings.allowed_network
                else "unchanged (allowed_network is unset)"
            ),
        }

    def apply(
        self,
        dry_run: bool = False,
        resource_assignments: Optional[dict[str, str]] = None,
        settings: Optional[ServerSettings] = None,
    ) -> dict:
        settings = settings or self.config.load()
        resource_profiles = self.config.load_resource_profiles()
        errors = settings.validate()
        if settings.allowed_network:
            try:
                ipaddress.ip_network(settings.allowed_network, strict=False)
            except ValueError:
                errors.append("allowed_network must be a valid IPv4 or IPv6 CIDR")
        if errors:
            raise ValueError("; ".join(errors))
        capacity = self.capacity(
            ['linux-light'] * settings.linux_session_slots
            + ['windows-standard'] * settings.windows_session_slots,
            settings=settings,
        )
        if not capacity["admissible"]:
            raise ValueError("configured session mix exceeds safe host memory capacity")
        if not dry_run:
            if settings.network_mode == "private" and not settings.allowed_network:
                raise ValueError("allowed_network is required for a production apply")
            required_files = (
                self.xrdp_ini,
                self.sesman_ini,
                Path(settings.tls_certificate),
                Path(settings.tls_key),
            )
            missing = [str(path) for path in required_files if not path.is_file()]
            if missing:
                raise FileNotFoundError("required server files are missing: " + ", ".join(missing))
            if not Path("/sys/fs/cgroup/cgroup.controllers").exists():
                raise RuntimeError("cgroup v2 is required")
            if settings.allowed_network and not shutil.which("nft"):
                raise RuntimeError("nft is required for private-network enforcement")
        payload = {
            "config_path": str(self.config.path),
            "config_content": ServerConfig.render(settings, resource_profiles),
            "xrdp_ini": str(self.xrdp_ini),
            "sesman_ini": str(self.sesman_ini),
            "settings": settings.to_dict(),
            "dry_run": dry_run,
            "resource_assignments": resource_assignments or {},
            "resource_profiles": resource_profiles,
        }
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            json.dump(payload, handle)
            payload_path = handle.name
        try:
            privilege = (
                []
                if dry_run or os.geteuid() == 0
                else get_privilege_command()[1]
            )
            result = self.command_runner(
                privilege + [sys.executable, str(self.helper_path), payload_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip())
            return json.loads(result.stdout)
        finally:
            Path(payload_path).unlink(missing_ok=True)

    def status(self, session_monitor=None) -> dict:
        services = {}
        for service in ("xrdp", "xrdp-sesman"):
            result = self.command_runner(
                ["systemctl", "is-active", service],
                capture_output=True,
                text=True,
                timeout=5,
            )
            services[service] = result.returncode == 0
        memory = psutil.virtual_memory()
        data = {
            "healthy": all(services.values()),
            "services": services,
            "cpu_percent": psutil.cpu_percent(interval=None),
            "memory_percent": memory.percent,
            "memory_available_mb": int(memory.available / (1024 * 1024)),
            "load_average": os.getloadavg() if hasattr(os, "getloadavg") else (),
        }
        if session_monitor:
            sessions = session_monitor.get_active_sessions()
            data["sessions"] = [item.to_dict() for item in sessions]
            data["active_sessions"] = len(sessions)
        return data

    def benchmark(self, samples: int = 5) -> dict:
        timings = []
        for _ in range(max(1, samples)):
            started = time.monotonic()
            self.status()
            timings.append((time.monotonic() - started) * 1000)
        timings.sort()
        p95_index = min(len(timings) - 1, int(len(timings) * 0.95))
        return {
            "samples": len(timings),
            "status_p95_ms": round(timings[p95_index], 2),
            "status_average_ms": round(sum(timings) / len(timings), 2),
        }
