#!/usr/bin/env python3
"""Privileged, narrowly-scoped applier for the RDPSM server profile."""

from __future__ import annotations

import json
import ipaddress
import os
import pwd
import shutil
import subprocess
import sys
import time
from pathlib import Path


ALLOWED_PATHS = {
    "/etc/rdp-session-manager/server.ini",
    "/etc/xrdp/xrdp.ini",
    "/etc/xrdp/sesman.ini",
}


def patch_ini(text: str, changes: dict[str, dict[str, str]]) -> str:
    lines = text.splitlines()
    output: list[str] = []
    current = ""
    seen: dict[str, set[str]] = {section: set() for section in changes}
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            if current in changes:
                for key, value in changes[current].items():
                    if key.lower() not in seen[current]:
                        output.append(f"{key}={value}")
            current = stripped[1:-1]
            output.append(line)
            continue
        replaced = False
        if current in changes and stripped and not stripped.startswith(("#", ";")) and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            for wanted, value in changes[current].items():
                if key.lower() == wanted.lower():
                    output.append(f"{wanted}={value}")
                    seen[current].add(wanted.lower())
                    replaced = True
                    break
        if not replaced:
            output.append(line)
    if current in changes:
        for key, value in changes[current].items():
            if key.lower() not in seen[current]:
                output.append(f"{key}={value}")
    for section, values in changes.items():
        if not any(line.strip().lower() == f"[{section}]".lower() for line in output):
            output.extend(["", f"[{section}]"])
            output.extend(f"{key}={value}" for key, value in values.items())
    return "\n".join(output) + "\n"


def atomic_write(path: Path, content: str, mode: int = 0o644) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.rdpsm-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    os.chmod(temporary, mode)
    os.replace(temporary, path)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: apply-server-profile.py PAYLOAD.json", file=sys.stderr)
        return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    settings = payload["settings"]
    paths = [payload["config_path"], payload["xrdp_ini"], payload["sesman_ini"]]
    if any(path not in ALLOWED_PATHS for path in paths):
        print("refusing path outside the RDPSM allowlist", file=sys.stderr)
        return 2
    if payload.get("dry_run"):
        print(json.dumps({"applied": False, "dry_run": True, "files": paths}))
        return 0
    if os.geteuid() != 0:
        print("root privileges are required", file=sys.stderr)
        return 1

    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup = Path("/var/backups/rdp-session-manager") / timestamp
    backup.mkdir(parents=True, exist_ok=False)
    originals: dict[Path, str | None] = {}
    for raw in paths:
        path = Path(raw)
        originals[path] = path.read_text(encoding="utf-8") if path.exists() else None
        if path.exists():
            shutil.copy2(path, backup / path.name)

    xrdp = patch_ini(
        originals[Path(payload["xrdp_ini"])] or "",
        {
            "Globals": {
                "security_layer": "tls",
                "crypt_level": "high",
                "tcp_nodelay": "true",
                "tcp_keepalive": "true",
                "bitmap_compression": "true",
                "bulk_compression": "true",
                "max_bpp": str(settings["max_bpp"]),
                "certificate": settings["tls_certificate"],
                "key_file": settings["tls_key"],
            }
        },
    )
    sesman = patch_ini(
        originals[Path(payload["sesman_ini"])] or "",
        {
            "Security": {
                "AllowRootLogin": "false",
                "TerminalServerUsers": "rdp-users",
                "AlwaysGroupCheck": "true",
            },
            "Sessions": {
                "MaxSessions": str(settings["max_sessions"]),
                "KillDisconnected": "true",
                "DisconnectedTimeLimit": str(settings["disconnected_timeout_seconds"]),
                "IdleTimeLimit": str(settings["idle_timeout_seconds"]),
            },
        },
    )
    slice_originals: dict[Path, str | None] = {}
    firewall_originals: dict[Path, str | None] = {}
    firewall_was_enabled = subprocess.run(
        ["systemctl", "is-enabled", "--quiet", "rdpsm-firewall.service"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    firewall_was_active = subprocess.run(
        ["systemctl", "is-active", "--quiet", "rdpsm-firewall.service"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
    try:
        atomic_write(Path(payload["config_path"]), payload["config_content"])
        atomic_write(Path(payload["xrdp_ini"]), xrdp)
        atomic_write(Path(payload["sesman_ini"]), sesman)
        slice_files = []
        profiles = payload.get("resource_profiles", {})
        for username, profile_name in payload.get("resource_assignments", {}).items():
            if profile_name not in profiles:
                raise ValueError(f"unknown resource profile: {profile_name}")
            account = pwd.getpwnam(username)
            if account.pw_uid < 1000:
                raise ValueError(f"refusing resource limits for system user: {username}")
            values = profiles[profile_name]
            dropin = (
                Path("/etc/systemd/system")
                / f"user-{account.pw_uid}.slice.d"
                / "50-rdpsm.conf"
            )
            if dropin not in slice_originals:
                slice_originals[dropin] = (
                    dropin.read_text(encoding="utf-8") if dropin.exists() else None
                )
                if dropin.exists():
                    shutil.copy2(dropin, backup / f"user-{account.pw_uid}.slice.conf")
            content = (
                "[Slice]\n"
                f"MemoryHigh={values['memory_high_mb']}M\n"
                f"MemoryMax={values['memory_max_mb']}M\n"
                f"CPUQuota={values['cpu_quota_percent']}%\n"
                f"TasksMax={values['tasks_max']}\n"
            )
            atomic_write(dropin, content)
            slice_files.append(str(dropin))
        if slice_files:
            subprocess.run(["systemctl", "daemon-reload"], check=True, timeout=30)
        firewall_files = []
        allowed_network = settings.get("allowed_network", "")
        if allowed_network:
            network = ipaddress.ip_network(allowed_network, strict=False)
            family = "ip6" if network.version == 6 else "ip"
            nft_path = Path("/etc/rdp-session-manager/rdpsm-firewall.nft")
            unit_path = Path("/etc/systemd/system/rdpsm-firewall.service")
            for path in (nft_path, unit_path):
                firewall_originals[path] = (
                    path.read_text(encoding="utf-8") if path.exists() else None
                )
                if path.exists():
                    shutil.copy2(path, backup / path.name)
            nft_content = (
                "table inet rdpsm {\n"
                "  chain input {\n"
                "    type filter hook input priority -10; policy accept;\n"
                f"    tcp dport 3389 {family} saddr != {network} drop\n"
                "  }\n"
                "}\n"
            )
            unit_content = (
                "[Unit]\nDescription=RDPSM private RDP firewall\n"
                "Before=xrdp.service\nAfter=network-pre.target\n"
                "[Service]\nType=oneshot\nRemainAfterExit=yes\n"
                f"ExecStartPre=-/usr/sbin/nft delete table inet rdpsm\n"
                f"ExecStart=/usr/sbin/nft -f {nft_path}\n"
                "ExecStop=-/usr/sbin/nft delete table inet rdpsm\n"
                "[Install]\nWantedBy=multi-user.target\n"
            )
            atomic_write(nft_path, nft_content, 0o600)
            atomic_write(unit_path, unit_content)
            subprocess.run(["nft", "-c", "-f", str(nft_path)], check=True, timeout=10)
            subprocess.run(["systemctl", "daemon-reload"], check=True, timeout=30)
            subprocess.run(
                ["systemctl", "enable", "--now", "rdpsm-firewall.service"],
                check=True,
                timeout=30,
            )
            firewall_files = [str(nft_path), str(unit_path)]
        for service in ("xrdp-sesman", "xrdp"):
            subprocess.run(["systemctl", "restart", service], check=True, timeout=30)
            subprocess.run(["systemctl", "is-active", "--quiet", service], check=True, timeout=10)
    except Exception:
        for path, content in originals.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
        for path, content in slice_originals.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
        if firewall_originals:
            subprocess.run(
                ["systemctl", "disable", "--now", "rdpsm-firewall.service"],
                check=False,
                timeout=30,
            )
        for path, content in firewall_originals.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                atomic_write(path, content)
        subprocess.run(["systemctl", "daemon-reload"], check=False, timeout=30)
        if firewall_was_enabled:
            subprocess.run(
                ["systemctl", "enable", "rdpsm-firewall.service"],
                check=False,
                timeout=30,
            )
        if firewall_was_active:
            subprocess.run(
                ["systemctl", "start", "rdpsm-firewall.service"],
                check=False,
                timeout=30,
            )
        for service in ("xrdp-sesman", "xrdp"):
            subprocess.run(["systemctl", "restart", service], check=False, timeout=30)
        raise

    print(json.dumps({
        "applied": True,
        "backup": str(backup),
        "files": paths,
        "resource_slices": slice_files,
        "firewall_files": firewall_files,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
