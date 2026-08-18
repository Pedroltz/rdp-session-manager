#!/usr/bin/env python3
"""Regression tests for the GTK health refresh controller."""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ui.main_window import MainWindow


class ImmediateThread:
    def __init__(self, target, daemon=False):
        self.target = target

    def start(self):
        self.target()


class HealthRefreshControllerTest(unittest.TestCase):
    def window_stub(self):
        window = Mock()
        window._health_refreshing = False
        window._last_health_report = None
        window.health_service.collect.return_value = Mock()
        return window

    @patch("ui.main_window.GLib.idle_add")
    @patch("threading.Thread", ImmediateThread)
    def test_idle_refresh_is_one_shot(self, idle_add):
        window = self.window_stub()
        result = MainWindow.refresh_health(window)
        self.assertFalse(result)
        window.health_spinner.start.assert_called_once()
        window.health_refresh_button.set_visible.assert_called_with(False)
        idle_add.assert_called_once()

    def test_overlapping_refresh_is_not_rescheduled(self):
        window = self.window_stub()
        window._health_refreshing = True
        self.assertFalse(MainWindow.refresh_health(window))
        window.health_service.collect.assert_not_called()


if __name__ == "__main__":
    unittest.main()
