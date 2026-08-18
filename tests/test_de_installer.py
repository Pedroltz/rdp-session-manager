#!/usr/bin/env python3
"""Tests for distribution-specific desktop installation."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.de_installer import DEInstaller
from core.desktop_environments import (
    SUPPORTED_DESKTOPS,
    detect_distro,
    get_desktop_info,
    get_startup_command,
)


class DesktopDefinitionsTest(unittest.TestCase):
    def test_supported_ids_are_strict(self):
        self.assertEqual(SUPPORTED_DESKTOPS, ("xfce", "gnome", "kde"))
        for removed in ("mate", "cinnamon", "lxde", "lxqt", "plasma", "xfce4"):
            self.assertIsNone(get_desktop_info(removed, "debian"))
            self.assertIsNone(get_desktop_info(removed, "arch"))

    def test_arch_uses_x11_compatible_sessions(self):
        self.assertEqual(get_startup_command("xfce", "arch"), "startxfce4")
        self.assertEqual(get_startup_command("kde", "arch"), "startplasma-x11")
        self.assertEqual(
            get_startup_command("gnome", "arch"),
            "gnome-session --session=gnome-flashback-metacity",
        )
        self.assertIn(
            "plasma-x11-session",
            get_desktop_info("kde", "arch")["packages"],
        )
        self.assertIn(
            "gnome-flashback",
            get_desktop_info("gnome", "arch")["packages"],
        )

    def test_detects_supported_families_and_derivatives(self):
        fixtures = {
            "ubuntu": ("debian", "ID=ubuntu\nID_LIKE=debian\nVERSION_ID=24.04\n"),
            "debian": ("debian", "ID=debian\nVERSION_ID=13\n"),
            "arch": ("arch", "ID=arch\n"),
            "manjaro": ("arch", "ID=manjaro\nID_LIKE=arch\n"),
            "endeavouros": ("arch", "ID=endeavouros\nID_LIKE=arch\n"),
            "cachyos": ("arch", "ID=cachyos\nID_LIKE=\"arch\"\n"),
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "os-release"
            for name, (family, content) in fixtures.items():
                with self.subTest(name=name):
                    path.write_text(content, encoding="utf-8")
                    self.assertEqual(detect_distro(path)["family"], family)


class DEInstallerTest(unittest.TestCase):
    def make_installer(self, family):
        installer = DEInstaller.__new__(DEInstaller)
        installer.distro_info = {
            "id": family,
            "family": family,
            "name": family.title(),
        }
        return installer

    @patch("core.de_installer.subprocess.run")
    def test_debian_detection_uses_dpkg_query(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="ii ", stderr="")
        installer = self.make_installer("debian")

        self.assertTrue(installer.is_de_installed("xfce"))
        self.assertEqual(
            run.call_args.args[0],
            ["/usr/bin/dpkg-query", "-W", "-f=${db:Status-Abbrev}", "xfce4"],
        )

    @patch("core.de_installer.subprocess.run")
    def test_arch_detection_uses_pacman(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        installer = self.make_installer("arch")

        self.assertTrue(installer.is_de_installed("xfce"))
        self.assertEqual(
            run.call_args.args[0],
            ["/usr/bin/pacman", "-Q", "xfce4-session"],
        )

    def test_list_contains_only_three_desktops(self):
        installer = self.make_installer("arch")
        with patch.object(installer, "is_de_installed", return_value=False):
            desktops = installer.get_available_des()
        self.assertEqual({item["id"] for item in desktops}, set(SUPPORTED_DESKTOPS))

    def test_arch_install_uses_full_upgrade_transaction(self):
        installer = self.make_installer("arch")
        completed = subprocess.CompletedProcess([], 0, stdout="done", stderr="")
        with (
            patch.object(installer, "is_de_installed", side_effect=[False, True]),
            patch.object(installer, "check_disk_space", return_value=(True, 600, 5000)),
            patch.object(installer, "_run_command", return_value=completed) as run_command,
            patch(
                "core.de_installer.get_privilege_command",
                return_value=("sudo", ["sudo"]),
            ),
        ):
            success, _ = installer.install_de("kde")

        self.assertTrue(success)
        command = run_command.call_args.args[0]
        child = command[command.index("--") + 1:]
        self.assertEqual(child[:5], ["/usr/bin/pacman", "-Syu", "--needed", "--noconfirm", "plasma-desktop"])
        self.assertIn("desktop.install", command)
        self.assertIn("plasma-x11-session", command)

    def test_debian_install_updates_then_installs(self):
        installer = self.make_installer("debian")
        completed = subprocess.CompletedProcess([], 0, stdout="done", stderr="")
        with (
            patch.object(installer, "is_de_installed", side_effect=[False, True]),
            patch.object(installer, "check_disk_space", return_value=(True, 600, 5000)),
            patch.object(installer, "_run_command", return_value=completed) as run_command,
            patch(
                "core.de_installer.get_privilege_command",
                return_value=("sudo", ["sudo"]),
            ),
        ):
            success, _ = installer.install_de("gnome")

        self.assertTrue(success)
        commands = [call.args[0] for call in run_command.call_args_list]
        first_child = commands[0][commands[0].index("--") + 1:]
        second_child = commands[1][commands[1].index("--") + 1:]
        self.assertEqual(first_child, ["/usr/bin/apt-get", "update"])
        self.assertEqual(
            second_child[:4],
            ["/usr/bin/apt-get", "install", "-y", "--no-install-recommends"],
        )

    def test_removed_desktop_is_rejected_before_package_manager(self):
        installer = self.make_installer("arch")
        with patch.object(installer, "_run_command") as run_command:
            success, message = installer.install_de("mate")
        self.assertFalse(success)
        self.assertIn("not supported", message)
        run_command.assert_not_called()

    def test_unknown_distribution_is_reported(self):
        installer = self.make_installer("unknown")
        success, message = installer.install_de("xfce")
        self.assertFalse(success)
        self.assertIn("not supported on", message)


if __name__ == "__main__":
    unittest.main()
