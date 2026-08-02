#!/usr/bin/env python3
"""Tests for server configuration, capacity, schema v2, and safe dispatch."""

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.server_config import ServerConfig, ServerSettings
from core.server_manager import ServerManager
from core.user_manager import ConnectionProfile, UserManager


def load_session_helper():
    path = Path(__file__).parent.parent / "helpers" / "rdpsm-session.py"
    spec = importlib.util.spec_from_file_location("rdpsm_session", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def load_apply_helper():
    path = Path(__file__).parent.parent / "helpers" / "apply-server-profile.py"
    spec = importlib.util.spec_from_file_location("apply_server_profile", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


class ServerConfigTest(unittest.TestCase):
    def test_defaults_are_production_bounded(self):
        settings = ServerSettings()
        self.assertEqual(settings.max_sessions, 25)
        self.assertEqual(settings.disconnected_timeout_seconds, 900)
        self.assertEqual(settings.idle_timeout_seconds, 3600)
        self.assertEqual(settings.validate(), [])

    def test_render_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "server.ini"
            path.write_text(ServerConfig.render(ServerSettings()), encoding="utf-8")
            loaded = ServerConfig(path).load()
        self.assertEqual(loaded, ServerSettings())

    def test_xrdp_patch_preserves_unrelated_sections(self):
        helper = load_apply_helper()
        original = "[Globals]\ntcp_nodelay=false\n\n[Xorg]\nname=Xorg\n"
        result = helper.patch_ini(
            original,
            {"Globals": {"tcp_nodelay": "true", "max_bpp": "24"}},
        )
        self.assertIn("tcp_nodelay=true", result)
        self.assertIn("max_bpp=24", result)
        self.assertIn("[Xorg]\nname=Xorg", result)

    @patch("core.server_manager.psutil.virtual_memory")
    def test_capacity_preserves_host_reserve(self, memory):
        memory.return_value = Mock(total=8 * 1024**3)
        manager = ServerManager(config_path="/nonexistent")
        accepted = manager.capacity(["linux-light"] * 5)
        rejected = manager.capacity(["windows-standard"] * 3)
        self.assertTrue(accepted["admissible"])
        self.assertFalse(rejected["admissible"])


class ProfileSchemaTest(unittest.TestCase):
    def test_legacy_command_is_migrated_to_argv_without_shell(self):
        profile = ConnectionProfile(
            "app", "App", "remoteapp", app_command="/usr/bin/example",
            app_args='--title "Quarterly Report"',
        )
        self.assertEqual(
            profile.command_argv,
            ["/usr/bin/example", "--title", "Quarterly Report"],
        )
        self.assertEqual(ConnectionProfile.from_dict(profile.to_dict()).command_argv, profile.command_argv)

    def test_loads_schema_v2_document(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".rdp_profiles.json").write_text(
                json.dumps({
                    "schema_version": 2,
                    "profiles": [{
                        "profile_id": "one",
                        "name": "One",
                        "profile_type": "remoteapp",
                        "command_argv": ["/usr/bin/true"],
                    }],
                }),
                encoding="utf-8",
            )
            manager = object.__new__(UserManager)
            profiles = manager.load_profiles_for_user(str(home))
        self.assertEqual(profiles[0].command_argv, ["/usr/bin/true"])


class SessionDispatcherTest(unittest.TestCase):
    def setUp(self):
        self.session = load_session_helper()

    def test_argv_does_not_interpret_shell_operators(self):
        profile = {
            "app_command": "/usr/bin/printf",
            "app_args": '"hello world" ; touch /tmp/not-created',
        }
        self.assertEqual(
            self.session.command_argv(profile),
            ["/usr/bin/printf", "hello world", ";", "touch", "/tmp/not-created"],
        )

    def test_rejects_unknown_requested_profile(self):
        with self.assertRaises(ValueError):
            self.session.select_profile(
                [{"profile_id": "known", "name": "Known"}],
                "unknown",
            )

    def test_marks_successful_runtime_validation_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            manifest = home / ".windows_runtime.json"
            manifest.write_text(
                json.dumps({"migration_state": "ready_for_session_validation"}),
                encoding="utf-8",
            )
            self.session.mark_runtime_validated(home)
            result = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(result["migration_state"], "validated")
        self.assertIn("validated_at", result)


if __name__ == "__main__":
    unittest.main()
