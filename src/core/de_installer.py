#!/usr/bin/env python3
"""Desktop-environment installation for Debian and Arch families."""

import logging
import shutil
import subprocess
from typing import Dict, List, Optional, Tuple

from core.desktop_environments import (
    DESKTOPS,
    SUPPORTED_DESKTOPS,
    detect_distro,
    get_desktop_info,
    normalize_desktop_id,
)
from utils.polkit import get_privilege_command

logger = logging.getLogger(__name__)


class DEInstaller:
    """Install and inspect the desktop environments supported by RDPSM."""

    # Kept as a public compatibility attribute, now containing canonical IDs only.
    DE_PACKAGES = DESKTOPS

    def __init__(self):
        self.distro_info = self._detect_distro()

    def _detect_distro(self) -> Dict:
        return detect_distro()

    @property
    def family(self) -> str:
        return str(self.distro_info.get("family", "unknown"))

    def _info(self, de_id: str) -> Optional[Dict]:
        return get_desktop_info(normalize_desktop_id(de_id), self.family)

    def get_available_des(self) -> List[Dict]:
        desktops = []
        for de_id in SUPPORTED_DESKTOPS:
            info = self._info(de_id)
            if info is None:
                definition = DESKTOPS[de_id]
                info = {
                    "id": de_id,
                    "name": definition["name"],
                    "size_mb": max(definition["size_mb"].values()),
                }
            desktops.append(
                {
                    "id": de_id,
                    "name": info["name"],
                    "size_mb": info["size_mb"],
                    "installed": self.is_de_installed(de_id),
                }
            )
        return sorted(desktops, key=lambda item: item["size_mb"])

    def is_de_installed(self, de_id: str) -> bool:
        info = self._info(de_id)
        if info is None:
            return False

        try:
            if self.family == "arch":
                command = ["/usr/bin/pacman", "-Q", info["check_package"]]
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0:
                    return True

                group_command = ["/usr/bin/pacman", "-Qg", info["check_package"]]
                group_res = subprocess.run(
                    group_command, capture_output=True, text=True, timeout=10
                )
                if group_res.returncode == 0:
                    return True
            else:
                command = [
                    "/usr/bin/dpkg-query",
                    "-W",
                    "-f=${db:Status-Abbrev}",
                    info["check_package"],
                ]
                result = subprocess.run(
                    command, capture_output=True, text=True, timeout=10
                )
                if result.returncode == 0 and result.stdout.startswith("ii"):
                    return True

            first_cmd_binary = info["startup_cmd"].split()[0]
            if first_cmd_binary and shutil.which(first_cmd_binary):
                return True

            return False
        except (OSError, subprocess.SubprocessError) as exc:
            logger.error("Error checking installation of %s: %s", de_id, exc)
            return False

    def _run_command(self, command: List[str], timeout: int = 1800):
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

    def install_de(self, de_id: str, progress_callback=None) -> Tuple[bool, str]:
        def log(progress, message):
            if progress_callback:
                progress_callback(progress, message)
            logger.info(message)

        normalized = normalize_desktop_id(de_id)
        info = self._info(normalized)
        if normalized not in SUPPORTED_DESKTOPS:
            return False, (
                f"Desktop environment '{de_id}' is not supported. "
                f"Options: {', '.join(SUPPORTED_DESKTOPS)}"
            )
        if info is None:
            return False, (
                f"Desktop installation is not supported on "
                f"{self.distro_info.get('name', 'this distribution')}"
            )
        if self.is_de_installed(normalized):
            message = f"{info['name']} is already installed"
            log(100, f"OK {message}")
            return True, message

        has_space, required, available = self.check_disk_space(normalized)
        if not has_space:
            message = (
                f"Not enough disk space. Required: {required} MB, "
                f"available: {available} MB"
            )
            log(0, f"X {message}")
            return False, message

        try:
            privilege_method, privilege_command = get_privilege_command()
            auth_name = "pkexec" if privilege_method == "pkexec" else "sudo"
            packages = list(info["packages"])

            log(5, f"OK Available disk space: {available} MB")
            log(10, f"WARNING You may be asked to authenticate ({auth_name})")

            if self.family == "arch":
                install_command = privilege_command + [
                    "/usr/bin/pacman",
                    "-Syu",
                    "--needed",
                    "--noconfirm",
                    *packages,
                ]
                log(20, f"$ {auth_name} pacman -Syu --needed --noconfirm {' '.join(packages)}")
            else:
                update_command = privilege_command + ["/usr/bin/apt-get", "update"]
                log(10, f"$ {auth_name} apt-get update")
                update = self._run_command(update_command, timeout=300)
                if update.returncode != 0:
                    detail = (update.stderr or update.stdout).strip()
                    message = f"Package cache update failed: {detail or update.returncode}"
                    log(0, f"X {message}")
                    return False, message

                install_command = privilege_command + [
                    "/usr/bin/apt-get",
                    "install",
                    "-y",
                    "--no-install-recommends",
                    *packages,
                ]
                log(20, f"$ {auth_name} apt-get install -y --no-install-recommends {' '.join(packages)}")

            log(30, f"Installing {info['name']}...")
            result = self._run_command(install_command)
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                message = f"Installation failed: {detail or result.returncode}"
                log(0, f"X {message}")
                return False, message

            if not self.is_de_installed(normalized):
                message = "Package manager completed, but the desktop was not detected"
                log(0, f"X {message}")
                return False, message

            message = f"{info['name']} installed successfully"
            log(100, f"OK {message}")
            return True, message
        except subprocess.TimeoutExpired:
            message = f"Installation of {info['name']} timed out (30 minutes)"
            log(0, f"X {message}")
            return False, message
        except (OSError, subprocess.SubprocessError) as exc:
            message = f"Error installing {info['name']}: {exc}"
            log(0, f"X {message}")
            return False, message

    def get_de_info(self, de_id: str) -> Optional[Dict]:
        info = self._info(de_id)
        if info is None:
            return None
        info["installed"] = self.is_de_installed(de_id)
        return info

    def get_de_startup_command(self, de_id: str) -> Optional[str]:
        info = self._info(de_id)
        return str(info["startup_cmd"]) if info else None

    def check_disk_space(self, de_id: str) -> Tuple[bool, int, int]:
        info = self._info(de_id)
        if info is None:
            return False, 0, 0
        required_mb = int(info["size_mb"])
        try:
            available_mb = shutil.disk_usage("/").free // (1024 * 1024)
            required_with_margin = int(required_mb * 1.2)
            return available_mb >= required_with_margin, required_with_margin, available_mb
        except OSError as exc:
            logger.error("Error checking disk space: %s", exc)
            return False, required_mb, 0
