#!/usr/bin/env python3
"""Tests for managed-file repair snapshots and rollback."""

import importlib.util
import os
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location(
    "repair_transaction", ROOT / "helpers" / "repair-transaction.py"
)
transaction = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transaction)


class RepairTransactionTest(unittest.TestCase):
    def test_restore_recovers_files_symlinks_and_absent_state(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            backups = Path(directory) / "backups"
            home.mkdir()
            (home / ".xsession").write_text("old session\n", encoding="utf-8")
            (home / ".xinitrc").symlink_to(".xsession")
            snapshot = transaction.create_snapshot(home, backups)

            (home / ".xsession").write_text("broken\n", encoding="utf-8")
            (home / ".xinitrc").unlink()
            (home / ".xinitrc").write_text("not a link\n", encoding="utf-8")
            (home / ".rdp_profiles.json").write_text("new\n", encoding="utf-8")
            transaction.restore_snapshot(snapshot, home)

            self.assertEqual((home / ".xsession").read_text(), "old session\n")
            self.assertTrue((home / ".xinitrc").is_symlink())
            self.assertEqual(os.readlink(home / ".xinitrc"), ".xsession")
            self.assertFalse((home / ".rdp_profiles.json").exists())

    def test_restore_rejects_snapshot_for_another_home(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            other = Path(directory) / "other"
            home.mkdir()
            other.mkdir()
            snapshot = transaction.create_snapshot(home, Path(directory) / "backups")
            with self.assertRaises(ValueError):
                transaction.restore_snapshot(snapshot, other)


if __name__ == "__main__":
    unittest.main()
