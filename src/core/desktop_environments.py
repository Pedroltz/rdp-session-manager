#!/usr/bin/env python3
"""Canonical desktop-environment definitions shared by the application."""

from pathlib import Path
from typing import Dict, Optional


SUPPORTED_DESKTOPS = ("xfce", "gnome", "kde")

DESKTOPS = {
    "xfce": {
        "name": "XFCE",
        "size_mb": {"debian": 450, "arch": 500},
        "startup_cmd": {"debian": "startxfce4", "arch": "startxfce4"},
        "check_package": {"debian": "xfce4", "arch": "xfce4-session"},
        "packages": {
            "debian": [
                "xfce4",
                "xfce4-goodies",
                "xfce4-terminal",
                "thunar",
                "xfwm4",
                "xfce4-settings",
                "dbus-x11",
            ],
            "arch": ["xfce4", "xfce4-goodies", "dbus"],
        },
    },
    "gnome": {
        "name": "GNOME",
        "size_mb": {"debian": 1400, "arch": 1100},
        "startup_cmd": {
            "debian": "gnome-session --session=gnome-flashback-metacity",
            "arch": "gnome-session --session=gnome-flashback-metacity",
        },
        "check_package": {"debian": "gnome-flashback", "arch": "gnome-flashback"},
        "packages": {
            "debian": [
                "gnome-session-flashback",
                "gnome-flashback",
                "gnome-session",
                "gnome-shell",
                "gnome-terminal",
                "nautilus",
                "gnome-control-center",
                "gnome-tweaks",
                "mutter",
                "gnome-settings-daemon",
                "dbus-x11",
            ],
            "arch": [
                "gnome-flashback",
                "gnome-session",
                "gnome-terminal",
                "nautilus",
                "gnome-control-center",
                "gnome-tweaks",
                "dbus",
            ],
        },
    },
    "kde": {
        "name": "KDE Plasma",
        "size_mb": {"debian": 1800, "arch": 1800},
        "startup_cmd": {
            "debian": "startplasma-x11",
            "arch": "startplasma-x11",
        },
        "check_package": {
            "debian": "kde-plasma-desktop",
            "arch": "plasma-desktop",
        },
        "packages": {
            "debian": [
                "kde-plasma-desktop",
                "plasma-workspace",
                "plasma-session-x11",
                "kwin-x11",
                "konsole",
                "dolphin",
                "systemsettings",
                "plasma-desktop",
                "dbus-x11",
            ],
            "arch": [
                "plasma-desktop",
                "plasma-workspace",
                "plasma-x11-session",
                "konsole",
                "dolphin",
                "systemsettings",
                "dbus",
            ],
        },
    },
}


def normalize_desktop_id(de_id: str) -> str:
    """Normalize a desktop ID without accepting historical aliases."""
    return (de_id or "").strip().lower()


def detect_distro(os_release: Path = Path("/etc/os-release")) -> Dict[str, object]:
    """Return normalized distribution metadata and package family."""
    try:
        values = {}
        for raw_line in os_release.read_text(encoding="utf-8").splitlines():
            if "=" in raw_line:
                key, value = raw_line.split("=", 1)
                values[key] = value.strip().strip('"')

        identifier = values.get("ID", "unknown").lower()
        id_like = tuple(values.get("ID_LIKE", "").lower().split())
        candidates = {identifier, *id_like}

        if candidates & {"arch", "manjaro", "endeavouros", "cachyos"}:
            family = "arch"
        elif candidates & {"debian", "ubuntu"}:
            family = "debian"
        else:
            family = "unknown"

        return {
            "id": identifier,
            "id_like": id_like,
            "family": family,
            "version": values.get("VERSION_ID", "unknown"),
            "name": values.get("NAME", "Unknown"),
        }
    except (OSError, UnicodeError):
        return {
            "id": "unknown",
            "id_like": (),
            "family": "unknown",
            "version": "unknown",
            "name": "Unknown",
        }


def get_desktop_info(de_id: str, family: str) -> Optional[Dict[str, object]]:
    """Return a distribution-specific copy of a desktop definition."""
    normalized = normalize_desktop_id(de_id)
    definition = DESKTOPS.get(normalized)
    if definition is None or family not in {"debian", "arch"}:
        return None

    return {
        "id": normalized,
        "name": definition["name"],
        "size_mb": definition["size_mb"][family],
        "startup_cmd": definition["startup_cmd"][family],
        "check_package": definition["check_package"][family],
        "packages": list(definition["packages"][family]),
    }


def get_startup_command(de_id: str, family: Optional[str] = None) -> Optional[str]:
    """Return the correct session command for the current distribution."""
    selected_family = family or str(detect_distro()["family"])
    info = get_desktop_info(de_id, selected_family)
    return str(info["startup_cmd"]) if info else None
