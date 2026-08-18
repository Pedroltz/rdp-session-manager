#!/usr/bin/env python3
"""Unit tests for human-readable health evidence formatting."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ui.health_dialog import HealthDialog


class HealthDialogFormattingTest(unittest.TestCase):
    def test_lists_are_rendered_as_bullets_instead_of_json(self):
        rendered = HealthDialog._render_evidence(["first issue", "second issue"])
        self.assertEqual(rendered, "• first issue\n• second issue")

    def test_nested_capacity_is_rendered_as_named_lines(self):
        rendered = HealthDialog._render_evidence({
            "configured_limit_mb": 44800,
            "safe_host_budget_mb": 11053,
        })
        self.assertIn("Configured Limit Mb: 44800", rendered)
        self.assertIn("Safe Host Budget Mb: 11053", rendered)
        self.assertNotIn("{", rendered)


if __name__ == "__main__":
    unittest.main()
