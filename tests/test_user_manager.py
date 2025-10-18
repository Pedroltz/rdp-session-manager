#!/usr/bin/env python3
"""
Tests for UserManager module
"""

import unittest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.user_manager import UserManager, RDPUser


class TestUserManager(unittest.TestCase):
    """Test UserManager class"""

    def setUp(self):
        """Setup test fixtures"""
        self.user_manager = UserManager("/tmp/test-rdp-users")

    def test_rdp_user_to_dict(self):
        """Test RDPUser to_dict method"""
        user = RDPUser(
            username='testuser',
            uid=5000,
            home_dir='/tmp/testuser',
            desktop_env='xfce',
            rdp_port=3389,
            active=True
        )

        user_dict = user.to_dict()

        self.assertEqual(user_dict['username'], 'testuser')
        self.assertEqual(user_dict['uid'], 5000)
        self.assertTrue(user_dict['active'])

    def test_rdp_user_from_dict(self):
        """Test RDPUser from_dict method"""
        data = {
            'username': 'testuser',
            'uid': 5000,
            'home_dir': '/tmp/testuser',
            'desktop_env': 'xfce',
            'rdp_port': 3389,
            'active': False
        }

        user = RDPUser.from_dict(data)

        self.assertEqual(user.username, 'testuser')
        self.assertEqual(user.uid, 5000)
        self.assertFalse(user.active)

    def test_validate_username(self):
        """Test username validation"""
        self.assertTrue(self.user_manager._validate_username('validuser'))
        self.assertTrue(self.user_manager._validate_username('user123'))
        self.assertFalse(self.user_manager._validate_username('123user'))
        self.assertFalse(self.user_manager._validate_username('User'))
        self.assertFalse(self.user_manager._validate_username('ab'))

    def test_get_next_uid(self):
        """Test UID generation"""
        uid = self.user_manager._get_next_uid()
        self.assertGreaterEqual(uid, UserManager.RDP_UID_START)

    def test_get_next_rdp_port(self):
        """Test RDP port generation"""
        port = self.user_manager._get_next_rdp_port(3389)
        self.assertGreaterEqual(port, 3389)


if __name__ == '__main__':
    unittest.main()
