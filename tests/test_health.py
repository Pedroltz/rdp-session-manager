#!/usr/bin/env python3
"""Tests for the unified RDPSM health contract."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli import CLI
from core.health import HealthCheck, HealthReport, HealthService


class FakeConfig:
    def load_resource_profiles(self):
        return {
            "linux-light": {"memory_max_mb": 1000},
            "windows-standard": {"memory_max_mb": 2500},
        }


class FakeServerManager:
    def __init__(self, services=None, memory=20.0, cpu=10.0):
        self.config = FakeConfig()
        self.services = services or {"xrdp": True, "xrdp-sesman": True}
        self.memory = memory
        self.cpu = cpu

    def status(self):
        return {
            "services": self.services,
            "memory_percent": self.memory,
            "cpu_percent": self.cpu,
        }

    def preflight(self):
        return {
            "errors": [],
            "warnings": [],
            "distribution": "ubuntu",
            "version": "24.04",
            "xrdp_version": "0.10.2",
            "settings": {"tls_certificate": "/missing/test-cert.pem"},
        }


class FakeUserManager:
    def __init__(self, users=None, issues=None):
        self.users = users or []
        self.issues = issues or {}

    def list_users(self):
        return list(self.users)

    def get_user(self, username):
        return next((user for user in self.users if user.username == username), None)

    def diagnose_user(self, username):
        return {
            "exists": True,
            "managed": True,
            "session_type": "desktop",
            "issues": list(self.issues.get(username, [])),
        }


class FakeSessionMonitor:
    def __init__(self, sessions=None):
        self.sessions = sessions or []

    def get_active_sessions(self):
        return list(self.sessions)


def fake_user(username="alice"):
    profile = SimpleNamespace(resource_profile="linux-light")
    return SimpleNamespace(
        username=username,
        enabled=True,
        default_profile=profile,
    )


class HealthContractTest(unittest.TestCase):
    def test_report_uses_highest_severity_and_stable_schema(self):
        report = HealthReport(
            "2026-08-10T12:00:00+00:00",
            [
                HealthCheck("ok", "host", "server", "healthy", "OK"),
                HealthCheck("warn", "host", "server", "warning", "Warning"),
            ],
        )
        payload = report.to_dict()
        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["overall_status"], "warning")
        self.assertEqual(payload["counts"]["healthy"], 1)
        self.assertEqual(payload["checks"][1]["id"], "warn")

    def test_invalid_status_is_rejected(self):
        with self.assertRaises(ValueError):
            HealthCheck("bad", "host", "server", "broken", "Bad")

    def test_filter_checks_combines_status_scope_and_search(self):
        report = HealthReport(
            "2026-08-10T12:00:00+00:00",
            [
                HealthCheck(
                    "host.disk", "host", "/", "warning", "Disk is nearly full",
                    {"mount": "/"},
                ),
                HealthCheck(
                    "user.account:alice", "user", "alice", "critical",
                    "Profile is missing", {"file": ".rdp_profiles.json"},
                ),
                HealthCheck(
                    "user.account:bob", "user", "bob", "healthy", "User is healthy",
                ),
            ],
        )
        self.assertEqual(
            [item.check_id for item in report.filter_checks("critical", "user", "rdp_profiles")],
            ["user.account:alice"],
        )
        self.assertEqual(
            [item.check_id for item in report.filter_checks(query="BOB")],
            ["user.account:bob"],
        )

    def test_filter_rejects_unknown_status(self):
        report = HealthReport("2026-08-10T12:00:00+00:00", [])
        with self.assertRaises(ValueError):
            report.filter_checks(status="broken")


class HealthServiceTest(unittest.TestCase):
    def service(self, server=None, users=None, sessions=None, issues=None, disk="/"):
        return HealthService(
            server or FakeServerManager(),
            FakeUserManager(users, issues),
            FakeSessionMonitor(sessions),
            disk_path=disk,
            now=lambda: datetime(2026, 8, 10, tzinfo=timezone.utc),
        )

    def test_connected_user_is_not_unhealthy_for_having_processes(self):
        user = fake_user()
        session = SimpleNamespace(
            username="alice", session_id="10", memory_mb=100.0,
            cpu_percent=3.0, process_count=4,
        )
        report = self.service(
            users=[user], sessions=[session],
            issues={"alice": ["User has active processes"]},
        ).collect("alice")
        account = next(check for check in report.checks if check.scope == "user")
        self.assertEqual(account.status, "healthy")
        self.assertTrue(account.evidence["connected"])

    def test_inactive_xrdp_service_is_critical(self):
        server = FakeServerManager(services={"xrdp": False, "xrdp-sesman": True})
        report = self.service(server=server).collect()
        check = next(item for item in report.checks if item.check_id == "host.service.xrdp")
        self.assertEqual(check.status, "critical")
        self.assertEqual(check.remediation_id, "restart-xrdp")

    def test_missing_requested_user_is_critical(self):
        report = self.service().collect("missing")
        self.assertEqual(report.overall_status, "critical")
        self.assertEqual(report.checks[0].check_id, "user.account:missing")

    def test_session_warns_near_memory_limit(self):
        user = fake_user()
        session = SimpleNamespace(
            username="alice", session_id="11", memory_mb=850.0,
            cpu_percent=8.0, process_count=5,
        )
        report = self.service(users=[user], sessions=[session]).collect("alice")
        check = next(item for item in report.checks if item.scope == "session")
        self.assertEqual(check.status, "warning")
        self.assertEqual(check.evidence["memory_limit_percent"], 85.0)

    def test_unreadable_disk_is_reported_as_unknown(self):
        report = self.service(disk="/definitely/missing/rdpsm").collect()
        check = next(item for item in report.checks if item.check_id == "host.disk")
        self.assertEqual(check.status, "unknown")

    def test_existing_unreadable_tls_certificate_is_unknown_not_broken(self):
        with tempfile.NamedTemporaryFile() as certificate:
            server = FakeServerManager()
            original = server.preflight
            server.preflight = lambda: {
                **original(),
                "settings": {"tls_certificate": certificate.name},
            }
            with patch("core.health.os.access", return_value=False):
                report = self.service(server=server).collect()
        check = next(item for item in report.checks if item.check_id == "host.tls")
        self.assertEqual(check.status, "unknown")
        self.assertIn("elevated", check.summary)


class HealthCliTest(unittest.TestCase):
    def test_json_output_and_exit_code_use_report_contract(self):
        cli = CLI()
        cli._health_service = SimpleNamespace(
            collect=lambda username=None: HealthReport(
                "2026-08-10T12:00:00+00:00",
                [HealthCheck("host.ok", "host", "server", "healthy", "OK")],
            )
        )
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.run(["health", "--format", "json"])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["overall_status"], "healthy")


if __name__ == "__main__":
    unittest.main()
