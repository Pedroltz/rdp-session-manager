#!/usr/bin/env python3
"""Tests for repair plan generation and stale-plan protection."""

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cli import CLI
from core.remediation import RemediationService


class DiagnosisManager:
    def __init__(self, diagnosis):
        self.diagnosis = dict(diagnosis)

    def diagnose_user(self, username):
        return dict(self.diagnosis)


def diagnosis(**overrides):
    values = {
        "exists": True,
        "managed": True,
        "active": False,
        "session_type": "desktop",
        "app_command": "",
        "issues": [],
    }
    values.update(overrides)
    return values


class RemediationServiceTest(unittest.TestCase):
    def service(self, values):
        return RemediationService(
            DiagnosisManager(values),
            now=lambda: datetime(2026, 8, 10, tzinfo=timezone.utc),
        )

    def test_plan_is_serializable_and_declares_irreversible_password_step(self):
        plan = self.service(diagnosis()).plan_user("alice")
        payload = plan.to_dict()
        self.assertTrue(payload["applicable"])
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["requires_privilege"])
        self.assertEqual(payload["steps"][-1]["id"], "reset-rdp-password")
        self.assertFalse(payload["steps"][-1]["reversible"])
        self.assertNotIn("password", payload)
        self.assertNotIn("credential", payload)

    def test_windows_plan_includes_runtime_validation(self):
        plan = self.service(diagnosis(
            session_type="winege-remoteapp",
            app_command="/opt/app.exe",
        )).plan_user("alice")
        runtime = next(step for step in plan.steps if step.step_id == "restore-windows-runtime")
        self.assertFalse(runtime.reversible)

    def test_active_user_blocks_repair(self):
        plan = self.service(diagnosis(
            active=True,
            issues=["User has active processes"],
        )).plan_user("alice")
        self.assertFalse(plan.applicable)
        self.assertIn("Disconnect the user", plan.blockers[0])
        self.assertEqual(plan.issues, [])

    def test_changed_diagnosis_invalidates_plan(self):
        manager = DiagnosisManager(diagnosis())
        service = RemediationService(manager)
        plan = service.plan_user("alice")
        manager.diagnosis["issues"] = ["Missing managed files"]
        valid, message = service.validate_user_plan(plan)
        self.assertFalse(valid)
        self.assertIn("changed", message)

    def test_unchanged_plan_validates(self):
        service = self.service(diagnosis(issues=["Missing managed files"]))
        plan = service.plan_user("alice")
        self.assertEqual(service.validate_user_plan(plan), (True, ""))


class RemediationCliTest(unittest.TestCase):
    def test_plan_mode_is_read_only_and_json_serializable(self):
        service = RemediationService(DiagnosisManager(diagnosis()))
        cli = CLI()
        cli._remediation_service = service
        output = io.StringIO()
        with redirect_stdout(output):
            exit_code = cli.run([
                "user", "repair", "alice", "--plan", "--format", "json"
            ])
        payload = json.loads(output.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload["target"], "alice")
        self.assertTrue(payload["applicable"])


if __name__ == "__main__":
    unittest.main()
