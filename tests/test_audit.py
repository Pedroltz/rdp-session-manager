#!/usr/bin/env python3
"""Tests for privileged JSONL audit storage and CLI filtering."""

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "src"))

from core.audit import AuditStore


def load_helper(name, filename):
    spec = importlib.util.spec_from_file_location(name, ROOT / "helpers" / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


audit_helper = load_helper("audit_event_helper", "audit-event.py")
audit_exec = load_helper("audit_exec_helper", "audit-exec.py")


class AuditStoreTest(unittest.TestCase):
    def test_append_event_has_required_fields_and_no_sensitive_payload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            event = audit_helper.append_event(
                path,
                action="user.repair",
                target="alice",
                result="success",
                plan_id="plan-1",
                actor="admin",
            )
            stored = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(stored, event)
        self.assertEqual(stored["schema_version"], 1)
        self.assertEqual(stored["actor"], "admin")
        self.assertNotIn("password", stored)
        self.assertNotIn("arguments", stored)

    def test_filters_and_exports_jsonl_with_private_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            events = [
                {"timestamp": "2026-08-09T12:00:00+00:00", "actor": "root",
                 "target": "alice", "action": "user.repair", "result": "failure"},
                {"timestamp": "2026-08-10T12:00:00+00:00", "actor": "admin",
                 "target": "alice", "action": "user.repair", "result": "success"},
                {"timestamp": "2026-08-10T13:00:00+00:00", "actor": "admin",
                 "target": "bob", "action": "user.delete", "result": "success"},
            ]
            path.write_text("\n".join(json.dumps(item) for item in events) + "\n")
            store = AuditStore(audit_path=path)
            selected = store.list_events(
                user="alice", result="success", since="2026-08-10T00:00:00Z"
            )
            output = Path(directory) / "export.jsonl"
            _, count = store.export(output, user="alice", limit=100)
            exported = output.read_text(encoding="utf-8").splitlines()
            mode = os.stat(output).st_mode & 0o777
        self.assertEqual(selected, [events[1]])
        self.assertEqual(count, 2)
        self.assertEqual(len(exported), 2)
        self.assertEqual(mode, 0o600)

    def test_invalid_limit_and_timestamp_are_rejected(self):
        store = AuditStore(audit_path="/does/not/exist")
        with self.assertRaises(ValueError):
            store.list_events(limit=0)
        with self.assertRaises(ValueError):
            store.list_events(since="not-a-date")

    @patch("core.audit.get_privilege_command", return_value=("sudo", ["sudo"]))
    @patch("pathlib.Path.open", side_effect=PermissionError)
    def test_permission_denied_uses_privileged_read_helper(self, _open, _privilege):
        runner = Mock(return_value=Mock(
            returncode=0,
            stdout='[{"timestamp":"2026-08-10T12:00:00Z","target":"alice"}]',
            stderr="",
        ))
        store = AuditStore(audit_path="/restricted/audit.jsonl", runner=runner)
        events = store.list_events(limit=10)
        self.assertEqual(events[0]["target"], "alice")
        command = runner.call_args.args[0]
        self.assertEqual(command[0], "sudo")
        self.assertEqual(command[-1], "read")

    @patch.object(audit_exec, "_audit_module")
    @patch.object(audit_exec.subprocess, "run")
    @patch.object(audit_exec.os, "geteuid", return_value=0)
    def test_audit_exec_records_result_without_forwarding_arguments_to_event(
        self, _geteuid, run, audit_module
    ):
        run.return_value.returncode = 9
        audit = Mock(AUDIT_PATH=Path("/audit.jsonl"))
        audit_module.return_value = audit
        status = audit_exec.main([
            "--action", "user.password.change",
            "--target", "alice",
            "--", "/helper", "alice:super-secret",
        ])
        self.assertEqual(status, 9)
        run.assert_called_once_with(["/helper", "alice:super-secret"], check=False)
        recorded = audit.append_event.call_args.kwargs
        self.assertEqual(recorded["result"], "failure")
        self.assertEqual(recorded["error_code"], "exit-9")
        self.assertNotIn("super-secret", repr(recorded))


if __name__ == "__main__":
    unittest.main()
