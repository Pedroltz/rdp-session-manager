#!/usr/bin/env python3
"""Tests for graphical and terminal privilege elevation selection."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import polkit


class TestPrivilegeSelection(unittest.TestCase):
    def setUp(self):
        self.original_cli_mode = polkit.is_cli_mode()
        polkit.set_cli_mode(False)

    def tearDown(self):
        polkit.set_cli_mode(self.original_cli_mode)

    @patch("utils.polkit.is_wsl", return_value=False)
    @patch("utils.polkit.shutil.which", return_value="/usr/bin/pkexec")
    @patch.dict("utils.polkit.os.environ", {}, clear=True)
    def test_headless_system_uses_interactive_terminal_sudo(self, _which, _wsl):
        method, command = polkit.get_privilege_command()

        self.assertEqual(method, "sudo")
        self.assertEqual(command, ["sudo"])
        self.assertNotIn("-n", command)
        self.assertNotIn("-S", command)
        self.assertNotIn("-A", command)

    @patch("utils.polkit.is_wsl", return_value=False)
    @patch("utils.polkit.shutil.which", return_value="/usr/bin/pkexec")
    @patch.dict("utils.polkit.os.environ", {"DISPLAY": ":0"}, clear=True)
    def test_display_without_session_bus_uses_sudo(self, _which, _wsl):
        self.assertEqual(polkit.get_privilege_command(), ("sudo", ["sudo"]))

    @patch("utils.polkit.is_wsl", return_value=False)
    @patch("utils.polkit.shutil.which", return_value="/usr/bin/pkexec")
    @patch.dict(
        "utils.polkit.os.environ",
        {
            "DISPLAY": ":0",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        },
        clear=True,
    )
    def test_graphical_session_uses_pkexec(self, _which, _wsl):
        self.assertEqual(
            polkit.get_privilege_command(),
            ("pkexec", ["pkexec", "--user", "root"]),
        )

    @patch("utils.polkit.is_wsl", return_value=False)
    @patch("utils.polkit.shutil.which", return_value="/usr/bin/pkexec")
    @patch.dict(
        "utils.polkit.os.environ",
        {
            "DISPLAY": ":0",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        },
        clear=True,
    )
    def test_cli_mode_always_uses_sudo(self, _which, _wsl):
        polkit.set_cli_mode(True)

        self.assertEqual(polkit.get_privilege_command(), ("sudo", ["sudo"]))

    @patch("utils.polkit.is_wsl", return_value=True)
    @patch("utils.polkit.shutil.which", return_value="/usr/bin/pkexec")
    @patch.dict(
        "utils.polkit.os.environ",
        {
            "DISPLAY": ":0",
            "DBUS_SESSION_BUS_ADDRESS": "unix:path=/run/user/1000/bus",
        },
        clear=True,
    )
    def test_wsl_uses_sudo_even_with_graphical_environment(self, _which, _wsl):
        self.assertEqual(polkit.get_privilege_command(), ("sudo", ["sudo"]))


if __name__ == "__main__":
    unittest.main()
