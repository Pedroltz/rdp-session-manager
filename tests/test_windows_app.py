#!/usr/bin/env python3
"""Tests for the isolated Windows application lifecycle."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.windows_app import (  # noqa: E402
    InstallRecipe,
    RecipeCatalog,
    WindowsAppError,
    WindowsAppManager,
    safe_app_id,
    sha256_file,
)
from core.user_manager import ConnectionProfile  # noqa: E402


class WindowsAppRecipeTest(unittest.TestCase):
    def test_recipe_roundtrip_and_validation(self):
        original = InstallRecipe(
            recipe_id="sample",
            name="Sample",
            installer_type="msi",
            silent_args=["/qn", "/norestart"],
            executable_patterns=["*/Sample.exe"],
        )
        restored = InstallRecipe.from_dict(original.to_dict())
        self.assertEqual(restored.recipe_id, "sample")
        self.assertEqual(restored.silent_args, ["/qn", "/norestart"])

    def test_remote_recipe_requires_https_and_checksum(self):
        with self.assertRaises(WindowsAppError):
            InstallRecipe.from_dict(
                {
                    "id": "bad",
                    "name": "Bad",
                    "source": {"url": "http://example.test/setup.exe"},
                }
            )

    def test_safe_app_id(self):
        self.assertEqual(safe_app_id("My Windows App!"), "my-windows-app")
        self.assertTrue(safe_app_id("!!!").startswith("app-"))

    def test_wine_system_and_updater_executables_are_auxiliary(self):
        self.assertTrue(
            WindowsAppManager._is_auxiliary(
                "/prefix/drive_c/Program Files/Internet Explorer/iexplore.exe"
            )
        )
        self.assertTrue(
            WindowsAppManager._is_auxiliary(
                "/prefix/drive_c/Program Files/Notepad++/updater/GUP.exe"
            )
        )


class WindowsAppManagerTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.home = Path(self.temporary.name)
        self.manager = WindowsAppManager(self.home, RecipeCatalog([]))

    def tearDown(self):
        self.temporary.cleanup()

    def test_stage_portable_and_discover(self):
        source = self.home / "incoming"
        source.mkdir()
        executable = source / "Example.exe"
        executable.write_bytes(b"MZexample")
        (source / "uninstall.exe").write_bytes(b"MZuninstaller")
        recipe = InstallRecipe(
            recipe_id="example",
            name="Example",
            installer_type="portable",
            runner="winege-legacy",
            executable_patterns=["*/Example.exe"],
        )
        app_id = self.manager.stage(recipe, source=source)
        candidates = self.manager.discover(app_id)
        self.assertEqual(len(candidates), 1)
        self.assertTrue(candidates[0]["path"].endswith("Example.exe"))
        self.assertIn("recipe-match", candidates[0]["reasons"])
        manifest = self.manager.load_manifest(app_id)
        self.assertEqual(manifest["source"]["sha256"], "")

    def test_checksum_is_recorded_for_local_file(self):
        source = self.home / "setup.exe"
        source.write_bytes(b"MZsetup")
        recipe = InstallRecipe(
            recipe_id="setup",
            name="Setup",
            installer_type="exe",
            runner="winege-legacy",
        )
        app_id = self.manager.stage(recipe, source=source)
        self.assertEqual(
            self.manager.load_manifest(app_id)["source"]["sha256"],
            sha256_file(source),
        )

    def test_portable_install_selects_final_executable(self):
        source = self.home / "Portable.exe"
        source.write_bytes(b"MZportable")
        recipe = InstallRecipe(
            recipe_id="portable-install",
            name="Portable install",
            installer_type="portable",
            runner="winege-legacy",
            executable_patterns=["*/Portable.exe"],
        )
        app_id = self.manager.stage(recipe, source=source)
        self.manager.create_prefix = lambda ignored: None
        state = self.manager.install(app_id, mode="portable")
        self.assertEqual(state["state"], "validating")
        self.assertTrue(
            self.manager.load_manifest(app_id)["executable"].endswith("Portable.exe")
        )

    def test_unknown_exe_requires_assisted_install(self):
        source = self.home / "UnknownSetup.exe"
        source.write_bytes(b"MZinstaller")
        recipe = InstallRecipe(
            recipe_id="unknown",
            name="Unknown",
            installer_type="exe",
            runner="winege-legacy",
        )
        app_id = self.manager.stage(recipe, source=source)
        self.manager.create_prefix = lambda ignored: None
        state = self.manager.install(app_id)
        self.assertEqual(state["state"], "awaiting_assisted_install")
        self.assertEqual(state["installer"], str(self.manager.app_dir(app_id) / "source" / source.name))

    def test_state_history_and_invalid_state(self):
        source = self.home / "portable.exe"
        source.write_bytes(b"MZ")
        recipe = InstallRecipe(
            recipe_id="portable",
            name="Portable",
            installer_type="portable",
            runner="winege-legacy",
        )
        app_id = self.manager.stage(recipe, source=source)
        state = self.manager.set_state(app_id, "validating", "Checking")
        self.assertEqual([item["state"] for item in state["history"]], ["staging", "validating"])
        with self.assertRaises(WindowsAppError):
            self.manager.set_state(app_id, "unknown")

    def test_runner_uses_private_writable_runtime_directory(self):
        source = self.home / "Runtime.exe"
        source.write_bytes(b"MZ")
        recipe = InstallRecipe(
            recipe_id="runtime",
            name="Runtime",
            installer_type="portable",
            runner="winege-legacy",
        )
        app_id = self.manager.stage(recipe, source=source)
        environment = self.manager.runner_environment(
            self.manager.load_manifest(app_id)
        )
        runtime = Path(environment["XDG_RUNTIME_DIR"])
        self.assertTrue(runtime.is_dir())
        self.assertEqual(runtime.stat().st_mode & 0o777, 0o700)

    def test_profile_serialization_keeps_windows_app_id(self):
        profile = ConnectionProfile(
            "profile",
            "Windows app",
            profile_type="winege-remoteapp",
            windows_app_id="sample",
        )
        restored = ConnectionProfile.from_dict(profile.to_dict())
        self.assertEqual(restored.windows_app_id, "sample")


if __name__ == "__main__":
    unittest.main()
