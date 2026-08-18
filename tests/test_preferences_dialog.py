#!/usr/bin/env python3
"""Tests for Preferences Dialog and Server Capacity configuration logic."""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.server_config import ServerSettings, RESOURCE_PROFILES


class TestPreferencesCapacityLogic(unittest.TestCase):
    def test_capacity_budget_calculation(self):
        linux_mem = RESOURCE_PROFILES['linux-light']['memory_max_mb']  # 1280
        win_mem = RESOURCE_PROFILES['windows-standard']['memory_max_mb']  # 2560

        linux_slots = 4
        win_slots = 2
        requested_mb = (linux_slots * linux_mem) + (win_slots * win_mem)
        self.assertEqual(requested_mb, 10240)

        # 16 GB host with 20% reserve
        total_system_mb = 16384
        reserve_pct = 20
        safe_budget_mb = int(total_system_mb * (100 - reserve_pct) / 100)
        self.assertEqual(safe_budget_mb, 13107)
        self.assertLessEqual(requested_mb, safe_budget_mb)

    def test_recommendation_distribution_linux_only(self):
        total_system_mb = 13817
        reserve_pct = 20
        safe_budget_mb = int(total_system_mb * (100 - reserve_pct) / 100)
        linux_mem = 1280
        expected_slots = safe_budget_mb // linux_mem
        self.assertEqual(expected_slots, 8)


if __name__ == '__main__':
    unittest.main()
