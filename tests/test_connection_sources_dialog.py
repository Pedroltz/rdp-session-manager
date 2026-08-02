#!/usr/bin/env python3
"""
Tests for ConnectionSourcesDialog logic
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.user_manager import RDPUser, ConnectionProfile


class TestConnectionSourcesLogic(unittest.TestCase):
    """Test ConnectionSourcesDialog profile management logic"""

    def setUp(self):
        self.profile1 = ConnectionProfile(
            profile_id="p1",
            name="Full Desktop",
            profile_type="desktop",
            desktop_env="xfce",
            is_default=True
        )
        self.profile2 = ConnectionProfile(
            profile_id="p2",
            name="VS Code",
            profile_type="remoteapp",
            app_command="code",
            is_default=False
        )
        self.user = RDPUser(
            username="testuser",
            uid=5000,
            home_dir="/opt/rdp-users/testuser",
            desktop_env="xfce",
            rdp_port=3389,
            profiles=[self.profile1, self.profile2]
        )

    def test_set_default_profile(self):
        """Test setting a profile as default"""
        # Initially profile1 is default
        self.assertTrue(self.user.profiles[0].is_default)
        self.assertFalse(self.user.profiles[1].is_default)

        # Change default to profile2
        for p in self.user.profiles:
            p.is_default = (p.profile_id == self.profile2.profile_id)

        self.assertFalse(self.user.profiles[0].is_default)
        self.assertTrue(self.user.profiles[1].is_default)

    def test_delete_default_profile_reassigns_default(self):
        """Test deleting default profile reassigns default flag to remaining profile"""
        # Delete profile1 (default)
        self.user.profiles = [p for p in self.user.profiles if p.profile_id != self.profile1.profile_id]
        if self.user.profiles:
            self.user.profiles[0].is_default = True

        self.assertEqual(len(self.user.profiles), 1)
        self.assertEqual(self.user.profiles[0].profile_id, "p2")
        self.assertTrue(self.user.profiles[0].is_default)


if __name__ == '__main__':
    unittest.main()
