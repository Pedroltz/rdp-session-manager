#!/usr/bin/env python3
"""Unified, read-only health diagnostics for RDPSM hosts and users."""

from __future__ import annotations

import ssl
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import psutil


HEALTH_SCHEMA_VERSION = 1
VALID_STATUSES = ("healthy", "warning", "critical", "unknown")
STATUS_PRIORITY = {"healthy": 0, "unknown": 1, "warning": 2, "critical": 3}


@dataclass(frozen=True)
class HealthCheck:
    check_id: str
    scope: str
    target: str
    status: str
    summary: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    remediation_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid health status: {self.status}")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.check_id,
            "scope": self.scope,
            "target": self.target,
            "status": self.status,
            "summary": self.summary,
            "evidence": self.evidence,
            "remediation_id": self.remediation_id or None,
        }


@dataclass(frozen=True)
class HealthReport:
    captured_at: str
    checks: List[HealthCheck]
    schema_version: int = HEALTH_SCHEMA_VERSION

    @property
    def overall_status(self) -> str:
        if not self.checks:
            return "unknown"
        return max(self.checks, key=lambda item: STATUS_PRIORITY[item.status]).status

    @property
    def counts(self) -> Dict[str, int]:
        return {
            status: sum(1 for check in self.checks if check.status == status)
            for status in VALID_STATUSES
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "captured_at": self.captured_at,
            "overall_status": self.overall_status,
            "counts": self.counts,
            "checks": [check.to_dict() for check in self.checks],
        }

    def filter_checks(
        self,
        status: str = "",
        scope: str = "",
        query: str = "",
    ) -> List[HealthCheck]:
        """Return checks matching GTK/CLI-friendly filters."""
        if status and status not in VALID_STATUSES:
            raise ValueError(f"Invalid health status filter: {status}")
        normalized_query = query.strip().casefold()
        result = []
        for check in self.checks:
            if status and check.status != status:
                continue
            if scope and check.scope != scope:
                continue
            searchable = " ".join((
                check.check_id,
                check.scope,
                check.target,
                check.summary,
                json.dumps(check.evidence, sort_keys=True, default=str),
            )).casefold()
            if normalized_query and normalized_query not in searchable:
                continue
            result.append(check)
        return result


class HealthService:
    """Collect one consistent health snapshot for CLI and GTK consumers."""

    def __init__(
        self,
        server_manager,
        user_manager,
        session_monitor,
        disk_path: str | Path = "/",
        now=None,
    ):
        self.server_manager = server_manager
        self.user_manager = user_manager
        self.session_monitor = session_monitor
        self.disk_path = Path(disk_path)
        self._now = now or (lambda: datetime.now(timezone.utc))

    def collect(self, username: Optional[str] = None) -> HealthReport:
        checks: List[HealthCheck] = []
        if username is None:
            checks.extend(self._host_checks())
        users = self._selected_users(username)
        sessions = self._sessions()
        if username:
            sessions = [session for session in sessions if session.username == username]
        checks.extend(self._user_checks(users, username, sessions))
        checks.extend(self._session_checks(sessions, users))
        return HealthReport(
            captured_at=self._now().isoformat(),
            checks=checks,
        )

    def _host_checks(self) -> List[HealthCheck]:
        checks: List[HealthCheck] = []
        try:
            status = self.server_manager.status()
        except Exception as exc:
            return [HealthCheck(
                "host.status", "host", "server", "unknown",
                "Server status could not be collected",
                {"error": str(exc)},
            )]

        for service, active in status.get("services", {}).items():
            checks.append(HealthCheck(
                f"host.service.{service}", "host", service,
                "healthy" if active else "critical",
                f"{service} is active" if active else f"{service} is inactive",
                {"active": bool(active)},
                "restart-xrdp" if not active else "",
            ))

        checks.append(self._threshold_check(
            "host.memory", "server", float(status.get("memory_percent", 0.0)),
            80.0, 90.0, "Memory usage", "%",
        ))
        checks.append(self._threshold_check(
            "host.cpu", "server", float(status.get("cpu_percent", 0.0)),
            85.0, 95.0, "CPU usage", "%",
        ))

        try:
            disk = psutil.disk_usage(str(self.disk_path))
            checks.append(self._threshold_check(
                "host.disk", str(self.disk_path), float(disk.percent),
                85.0, 95.0, "Disk usage", "%",
            ))
        except OSError as exc:
            checks.append(HealthCheck(
                "host.disk", "host", str(self.disk_path), "unknown",
                "Disk usage could not be collected", {"error": str(exc)},
            ))

        checks.extend(self._preflight_checks())
        return checks

    def _preflight_checks(self) -> List[HealthCheck]:
        try:
            preflight = self.server_manager.preflight()
        except Exception as exc:
            return [HealthCheck(
                "host.preflight", "host", "server", "unknown",
                "Production readiness could not be evaluated",
                {"error": str(exc)},
            )]

        errors = list(preflight.get("errors", []))
        warnings = list(preflight.get("warnings", []))
        evidence = {"errors": errors, "warnings": warnings}
        capacity = preflight.get("capacity", {})
        if capacity:
            evidence["capacity"] = {
                "configured_sessions": capacity.get("requested_sessions"),
                "configured_limit_mb": capacity.get("requested_memory_max_mb"),
                "safe_host_budget_mb": capacity.get("safe_memory_mb"),
                "system_memory_mb": capacity.get("system_memory_mb"),
            }
        if errors:
            readiness = HealthCheck(
                "host.preflight", "host", "server", "critical",
                f"Production readiness has {len(errors)} blocking issue(s)",
                evidence,
                "apply-server-profile",
            )
        elif warnings:
            readiness = HealthCheck(
                "host.preflight", "host", "server", "warning",
                f"Production readiness has {len(warnings)} warning(s)",
                evidence,
            )
        else:
            readiness = HealthCheck(
                "host.preflight", "host", "server", "healthy",
                "Production readiness checks passed",
                {
                    "distribution": preflight.get("distribution"),
                    "version": preflight.get("version"),
                    "xrdp_version": preflight.get("xrdp_version"),
                },
            )

        tls = self._tls_check(preflight)
        return [readiness, tls]

    def _tls_check(self, preflight: Dict[str, Any]) -> HealthCheck:
        settings = preflight.get("settings", {})
        certificate = Path(settings.get("tls_certificate", "/etc/xrdp/cert.pem"))
        if not certificate.is_file():
            return HealthCheck(
                "host.tls", "host", str(certificate), "critical",
                "TLS certificate is missing", {}, "configure-tls",
            )
        if not os.access(certificate, os.R_OK):
            return HealthCheck(
                "host.tls", "host", str(certificate), "unknown",
                "TLS certificate exists but requires elevated access to inspect",
                {
                    "path": str(certificate),
                    "readable_by_current_user": False,
                    "reason": "Certificate contents were not read without administrator privileges",
                },
            )
        try:
            decoded = ssl._ssl._test_decode_cert(str(certificate))  # type: ignore[attr-defined]
            expires = datetime.strptime(
                decoded["notAfter"], "%b %d %H:%M:%S %Y %Z"
            ).replace(tzinfo=timezone.utc)
            days = int((expires - self._now()).total_seconds() / 86400)
        except (KeyError, OSError, TypeError, ValueError, ssl.SSLError) as exc:
            return HealthCheck(
                "host.tls", "host", str(certificate), "critical",
                "TLS certificate could not be parsed",
                {"path": str(certificate), "error_type": type(exc).__name__},
                "configure-tls",
            )
        status = "critical" if days < 7 else "warning" if days < 30 else "healthy"
        return HealthCheck(
            "host.tls", "host", str(certificate), status,
            f"TLS certificate expires in {days} day(s)",
            {"expires_at": expires.isoformat(), "days_remaining": days},
            "configure-tls" if status != "healthy" else "",
        )

    def _selected_users(self, username: Optional[str]) -> List[Any]:
        try:
            if username:
                user = self.user_manager.get_user(username)
                return [user] if user else []
            return list(self.user_manager.list_users())
        except Exception:
            return []

    def _sessions(self) -> List[Any]:
        try:
            return list(self.session_monitor.get_active_sessions())
        except Exception:
            return []

    def _user_checks(
        self,
        users: Iterable[Any],
        requested_username: Optional[str],
        sessions: Iterable[Any],
    ) -> List[HealthCheck]:
        users = list(users)
        if requested_username and not users:
            return [HealthCheck(
                f"user.account:{requested_username}", "user", requested_username,
                "critical", "Managed RDP user was not found",
                {}, "create-user",
            )]
        connected = {session.username for session in sessions}
        checks = []
        for user in users:
            try:
                diagnosis = self.user_manager.diagnose_user(user.username)
            except Exception as exc:
                checks.append(HealthCheck(
                    f"user.account:{user.username}", "user", user.username,
                    "unknown", "User diagnosis could not be collected",
                    {"error": str(exc)},
                ))
                continue
            issues = [
                issue for issue in diagnosis.get("issues", [])
                if issue != "User has active processes"
            ]
            healthy = bool(diagnosis.get("managed")) and not issues
            checks.append(HealthCheck(
                f"user.account:{user.username}", "user", user.username,
                "healthy" if healthy else "critical",
                "Managed user configuration is healthy" if healthy
                else f"Managed user has {len(issues)} issue(s)",
                {
                    "enabled": bool(getattr(user, "enabled", True)),
                    "connected": user.username in connected,
                    "issues": issues,
                    "session_type": diagnosis.get("session_type"),
                },
                "repair-user" if not healthy else "",
            ))
        return checks

    def _session_checks(self, sessions: Iterable[Any], users: Iterable[Any]) -> List[HealthCheck]:
        resource_profiles = self.server_manager.config.load_resource_profiles()
        by_name = {user.username: user for user in users}
        checks = []
        for session in sessions:
            user = by_name.get(session.username)
            profile_name = (
                getattr(getattr(user, "default_profile", None), "resource_profile", "linux-light")
                if user else "linux-light"
            )
            limit = resource_profiles.get(profile_name, {}).get("memory_max_mb", 0)
            memory = float(getattr(session, "memory_mb", 0.0))
            ratio = (memory / limit * 100.0) if limit else 0.0
            status = "critical" if ratio >= 95 else "warning" if ratio >= 80 else "healthy"
            checks.append(HealthCheck(
                f"session.resource:{session.username}", "session", session.username,
                status,
                f"Session is connected using {memory:.1f} MB",
                {
                    "session_id": getattr(session, "session_id", ""),
                    "memory_mb": round(memory, 2),
                    "memory_limit_mb": limit,
                    "memory_limit_percent": round(ratio, 2),
                    "cpu_percent": round(float(getattr(session, "cpu_percent", 0.0)), 2),
                    "process_count": int(getattr(session, "process_count", 0)),
                },
                "terminate-session" if status == "critical" else "",
            ))
        return checks

    @staticmethod
    def _threshold_check(
        check_id: str,
        target: str,
        value: float,
        warning: float,
        critical: float,
        label: str,
        unit: str,
    ) -> HealthCheck:
        status = "critical" if value >= critical else "warning" if value >= warning else "healthy"
        return HealthCheck(
            check_id, "host", target, status,
            f"{label} is {value:.1f}{unit}",
            {"value": round(value, 2), "warning_threshold": warning, "critical_threshold": critical},
        )
