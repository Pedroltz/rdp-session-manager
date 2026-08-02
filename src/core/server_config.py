#!/usr/bin/env python3
"""System-wide configuration for server-oriented RDP deployments."""

from __future__ import annotations

import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict


RESOURCE_PROFILES = {
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


@dataclass(frozen=True)
class ServerSettings:
    max_sessions: int = 25
    disconnected_timeout_seconds: int = 900
    idle_timeout_seconds: int = 3600
    max_bpp: int = 24
    memory_reserve_percent: int = 20
    linux_session_slots: int = 15
    windows_session_slots: int = 10
    network_mode: str = "private"
    allowed_network: str = ""
    tls_certificate: str = "/etc/xrdp/cert.pem"
    tls_key: str = "/etc/xrdp/key.pem"

    @classmethod
    def from_parser(cls, parser: configparser.ConfigParser) -> "ServerSettings":
        section = parser["server"] if parser.has_section("server") else {}

        def integer(key: str, default: int) -> int:
            try:
                return int(section.get(key, default))
            except (TypeError, ValueError):
                return default

        return cls(
            max_sessions=integer("max_sessions", 25),
            disconnected_timeout_seconds=integer("disconnected_timeout_seconds", 900),
            idle_timeout_seconds=integer("idle_timeout_seconds", 3600),
            max_bpp=integer("max_bpp", 24),
            memory_reserve_percent=integer("memory_reserve_percent", 20),
            linux_session_slots=integer("linux_session_slots", 15),
            windows_session_slots=integer("windows_session_slots", 10),
            network_mode=section.get("network_mode", "private"),
            allowed_network=section.get("allowed_network", ""),
            tls_certificate=section.get("tls_certificate", "/etc/xrdp/cert.pem"),
            tls_key=section.get("tls_key", "/etc/xrdp/key.pem"),
        )

    def validate(self) -> list[str]:
        errors = []
        if not 1 <= self.max_sessions <= 200:
            errors.append("max_sessions must be between 1 and 200")
        if self.disconnected_timeout_seconds < 60:
            errors.append("disconnected_timeout_seconds must be at least 60")
        if self.idle_timeout_seconds < 60:
            errors.append("idle_timeout_seconds must be at least 60")
        if self.max_bpp not in (16, 24, 32):
            errors.append("max_bpp must be 16, 24, or 32")
        if not 5 <= self.memory_reserve_percent <= 50:
            errors.append("memory_reserve_percent must be between 5 and 50")
        if self.linux_session_slots < 0 or self.windows_session_slots < 0:
            errors.append("session slots cannot be negative")
        if self.linux_session_slots + self.windows_session_slots > self.max_sessions:
            errors.append("Linux and Windows session slots exceed max_sessions")
        if self.network_mode != "private":
            errors.append("only the private network mode is production-supported")
        return errors

    def to_dict(self) -> Dict[str, object]:
        return dict(self.__dict__)


class ServerConfig:
    """Read system configuration without requiring write access to /etc."""

    def __init__(self, path: str | Path = "/etc/rdp-session-manager/server.ini"):
        self.path = Path(path)

    def load(self) -> ServerSettings:
        parser = configparser.ConfigParser()
        if self.path.exists():
            parser.read(self.path)
        return ServerSettings.from_parser(parser)

    def load_resource_profiles(self) -> Dict[str, Dict[str, int]]:
        parser = configparser.ConfigParser()
        if self.path.exists():
            parser.read(self.path)
        profiles = {name: dict(values) for name, values in RESOURCE_PROFILES.items()}
        for name, defaults in profiles.items():
            section = f"resource:{name}"
            if not parser.has_section(section):
                continue
            for key in defaults:
                try:
                    value = parser.getint(section, key)
                except (ValueError, configparser.Error):
                    continue
                if value > 0:
                    defaults[key] = value
        return profiles

    @staticmethod
    def render(
        settings: ServerSettings,
        resource_profiles: Dict[str, Dict[str, int]] | None = None,
    ) -> str:
        resource_profiles = resource_profiles or RESOURCE_PROFILES
        parser = configparser.ConfigParser()
        parser["server"] = {key: str(value) for key, value in settings.to_dict().items()}
        for name, values in resource_profiles.items():
            parser[f"resource:{name}"] = {
                key: str(value) for key, value in values.items()
            }
        from io import StringIO

        output = StringIO()
        parser.write(output)
        return output.getvalue()
