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
        # UserManager now receives app_config as first parameter, rdp_users_home as second
        self.user_manager = UserManager(app_config=None, rdp_users_home="/tmp/test-rdp-users")

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
        self.assertTrue(user_dict['enabled'])
        self.assertFalse(user_dict['is_superuser'])

    def test_rdp_user_to_dict_full(self):
        """Test RDPUser to_dict with all fields"""
        user = RDPUser(
            username='adminuser',
            uid=5001,
            home_dir='/tmp/adminuser',
            desktop_env='gnome',
            rdp_port=3390,
            active=True,
            enabled=False,
            is_superuser=True
        )

        user_dict = user.to_dict()

        self.assertEqual(user_dict['username'], 'adminuser')
        self.assertEqual(user_dict['uid'], 5001)
        self.assertEqual(user_dict['desktop_env'], 'gnome')
        self.assertEqual(user_dict['rdp_port'], 3390)
        self.assertTrue(user_dict['active'])
        self.assertFalse(user_dict['enabled'])
        self.assertTrue(user_dict['is_superuser'])

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

    def test_rdp_user_from_dict_full(self):
        """Test RDPUser from_dict with all fields"""
        data = {
            'username': 'poweruser',
            'uid': 5002,
            'home_dir': '/opt/rdp-users/poweruser',
            'desktop_env': 'kde',
            'rdp_port': 3391,
            'active': True,
            'enabled': True,
            'is_superuser': False
        }

        user = RDPUser.from_dict(data)

        self.assertEqual(user.username, 'poweruser')
        self.assertEqual(user.uid, 5002)
        self.assertEqual(user.home_dir, '/opt/rdp-users/poweruser')
        self.assertEqual(user.desktop_env, 'kde')
        self.assertEqual(user.rdp_port, 3391)
        self.assertTrue(user.active)
        self.assertTrue(user.enabled)
        self.assertFalse(user.is_superuser)

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
        # _detect_rdp_port now receives UID and returns port based on global config
        port = self.user_manager._detect_rdp_port(5001)
        self.assertEqual(port, 3389) # Must return the default port

    def test_rdp_user_defaults(self):
        """Test RDPUser default values"""
        user = RDPUser(
            username='defaultuser',
            uid=5003,
            home_dir='/tmp/defaultuser',
            desktop_env='lxde',
            rdp_port=3389
        )

        # Check defaults
        self.assertFalse(user.active)
        self.assertTrue(user.enabled)
        self.assertFalse(user.is_superuser)

    def test_rdp_user_serialization_roundtrip(self):
        """Test RDPUser serialization and deserialization"""
        original_user = RDPUser(
            username='roundtripuser',
            uid=5004,
            home_dir='/opt/rdp-users/roundtripuser',
            desktop_env='mate',
            rdp_port=3392,
            active=True,
            enabled=False,
            is_superuser=True
        )

        # Convert to dict and back
        user_dict = original_user.to_dict()
        restored_user = RDPUser.from_dict(user_dict)

        # Check that all values ​​have been preserved
        self.assertEqual(restored_user.username, original_user.username)
        self.assertEqual(restored_user.uid, original_user.uid)
        self.assertEqual(restored_user.home_dir, original_user.home_dir)
        self.assertEqual(restored_user.desktop_env, original_user.desktop_env)
        self.assertEqual(restored_user.rdp_port, original_user.rdp_port)
        self.assertEqual(restored_user.active, original_user.active)
        self.assertEqual(restored_user.enabled, original_user.enabled)
        self.assertEqual(restored_user.is_superuser, original_user.is_superuser)

    @patch('grp.getgrnam')
    def test_ensure_rdp_group_exists(self, mock_getgrnam):
        """Test that RDP group check works when group exists"""
        # Simulate existing group
        mock_group = Mock()
        mock_group.gr_gid = 1001
        mock_getgrnam.return_value = mock_group

        gid = self.user_manager._ensure_rdp_group()

        self.assertEqual(gid, 1001)
        mock_getgrnam.assert_called_once_with('rdp-users')

    @patch('grp.getgrnam')
    def test_ensure_rdp_group_not_exists(self, mock_getgrnam):
        """Test that RDP group check fails when group doesn't exist"""
        # Simulate non-existing group
        mock_getgrnam.side_effect = KeyError('rdp-users')

        gid = self.user_manager._ensure_rdp_group()

        self.assertEqual(gid, -1)

    def test_validate_username_edge_cases(self):
        """Test username validation edge cases"""
        # Limit case: 3 characters (minimum)
        self.assertTrue(self.user_manager._validate_username('abc'))

        # Limit case: 32 characters (maximum)
        self.assertTrue(self.user_manager._validate_username('a' * 32))

        # Too long: 33 characters
        self.assertFalse(self.user_manager._validate_username('a' * 33))

        # Valid special characters
        self.assertTrue(self.user_manager._validate_username('user-name'))
        self.assertTrue(self.user_manager._validate_username('user_name'))

        # Invalid special characters
        self.assertFalse(self.user_manager._validate_username('user@name'))
        self.assertFalse(self.user_manager._validate_username('user.name'))


if __name__ == '__main__':
    unittest.main()
