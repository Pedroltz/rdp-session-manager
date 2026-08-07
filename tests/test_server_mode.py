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

    @patch("core.server_manager.subprocess.Popen")
    @patch("core.server_manager.subprocess.run")
    def test_select_profile_invokes_chooser_for_multiple_profiles(self, mock_run, mock_popen):
        profiles = [
            {"profile_id": "p1", "name": "Desktop", "profile_type": "desktop", "is_default": True},
            {"profile_id": "p2", "name": "WineGE App", "profile_type": "winege-remoteapp", "is_default": False},
        ]
        mock_run.return_value = Mock(returncode=0, stdout=json.dumps(profiles[1]))
        with patch.object(Path, "exists", return_value=True):
            selected = self.session.select_profile(profiles, "")

        self.assertEqual(selected, profiles[1])
        mock_popen.assert_called_once_with(["openbox"], start_new_session=True)
        mock_run.assert_called_once()

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

    def test_umu_runtime_requires_marker_platform_and_proton(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "umu" / "steamrt3"
            proton = root / "Steam" / "compatibilitytools.d" / "UMU-Proton"
            runtime.mkdir(parents=True)
            proton.mkdir(parents=True)

            self.assertFalse(self.session.umu_runtime_ready(root))
            (runtime / ".installed.ok").touch()
            (runtime / "sniper_platform_123").mkdir()
            (proton / "toolmanifest.vdf").touch()

            self.assertTrue(self.session.umu_runtime_ready(root))

    def test_runtime_manifest_selects_system_wine_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            executable = home / "notepad.exe"
            executable.touch()
            (home / ".windows_runtime.json").write_text(
                json.dumps({"runtime": "wine"}),
                encoding="utf-8",
            )
            profile = {
                "profile_type": "winege-remoteapp",
                "runtime": "umu",
                "command_argv": [str(executable)],
            }
            with patch.object(self.session.shutil, "which", return_value="/usr/bin/wine"):
                argv = self.session.runtime_argv(profile, home)

        self.assertEqual(argv, ["/usr/bin/wine", str(executable)])

    def test_system_wine_ignores_stale_installer_wrapper(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            installed = home / ".wine" / "drive_c" / "Program Files" / "App" / "App.exe"
            installed.parent.mkdir(parents=True)
            installed.touch()
            (home / ".winege_app_path").write_text(
                f"{installed}\n",
                encoding="utf-8",
            )
            (home / ".windows_runtime.json").write_text(
                json.dumps({"runtime": "wine"}),
                encoding="utf-8",
            )
            wrapper = home / ".launch_winege_app.sh"
            wrapper.write_text(
                '#!/bin/bash\nexec wine "/old/Installer.exe"\n',
                encoding="utf-8",
            )
            profile = {
                "profile_id": "default",
                "profile_type": "winege-remoteapp",
                "runtime": "umu",
                "command_argv": ["/old/Installer.exe"],
            }

            with patch.object(self.session.shutil, "which", return_value="/usr/bin/wine"):
                argv = self.session.runtime_argv(profile, home)

        self.assertEqual(argv, ["/usr/bin/wine", str(installed)])

    def test_promotes_new_program_files_executable_after_installer(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            prefix = home / ".wine"
            application = prefix / "drive_c" / "Program Files" / "Notepad++" / "notepad++.exe"
            updater = application.parent / "updater" / "GUP.exe"
            application.parent.mkdir(parents=True)
            updater.parent.mkdir()
            (home / ".windows_runtime.json").write_text(
                json.dumps({"runtime": "wine", "executable": "setup.exe"}),
                encoding="utf-8",
            )
            (home / ".rdp_profiles.json").write_text(
                json.dumps({
                    "schema_version": 2,
                    "profiles": [{
                        "profile_id": "notepad",
                        "profile_type": "winege-remoteapp",
                        "app_command": "setup.exe",
                        "command_argv": ["setup.exe", "--example"],
                        "is_default": True,
                    }],
                }),
                encoding="utf-8",
            )

            before = self.session.installed_executables(prefix)
            application.write_bytes(b"MZ" + (b"a" * 4096))
            updater.write_bytes(b"MZ" + (b"b" * 8192))
            selected = self.session.promote_installed_executable(
                home, prefix, before, "notepad"
            )

            self.assertEqual(selected, application)
            self.assertEqual(
                (home / ".winege_app_path").read_text(encoding="utf-8").strip(),
                str(application),
            )
            manifest = json.loads(
                (home / ".windows_runtime.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["executable"], str(application))
            profiles = json.loads(
                (home / ".rdp_profiles.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                profiles["profiles"][0]["command_argv"],
                [str(application), "--example"],
            )

    def test_does_not_promote_unchanged_existing_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            prefix = home / ".wine"
            application = prefix / "drive_c" / "Program Files" / "Example" / "Example.exe"
            application.parent.mkdir(parents=True)
            application.write_bytes(b"MZapplication")
            before = self.session.installed_executables(prefix)

            selected = self.session.promote_installed_executable(home, prefix, before)

            self.assertIsNone(selected)
            self.assertFalse((home / ".winege_app_path").exists())

    def test_installer_can_promote_application_installed_in_previous_session(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            prefix = home / ".wine"
            application = prefix / "drive_c" / "Program Files" / "Example" / "Example.exe"
            application.parent.mkdir(parents=True)
            application.write_bytes(b"MZapplication")
            before = self.session.installed_executables(prefix)

            selected = self.session.promote_installed_executable(
                home, prefix, before, allow_existing=True
            )

            self.assertEqual(selected, application)


if __name__ == "__main__":
    unittest.main()
