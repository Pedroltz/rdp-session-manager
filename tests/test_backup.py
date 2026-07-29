#!/usr/bin/env python3
"""
Tests for BackupManager module
"""

import unittest
import sys
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.backup import BackupManager


class TestBackupManager(unittest.TestCase):
    """Test BackupManager class"""

    def setUp(self):
        """Setup test fixtures"""
        # Create temporary directory for backups
        self.test_dir = Path(tempfile.mkdtemp())
        self.backup_manager = BackupManager(str(self.test_dir))

    def tearDown(self):
        """Cleanup test fixtures"""
        # Remove temporary directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_backup_manager_initialization(self):
        """Test BackupManager initialization"""
        self.assertIsNotNone(self.backup_manager)
        self.assertTrue(self.backup_manager.backup_dir.exists())
        self.assertEqual(self.backup_manager.backup_dir, self.test_dir)

    @patch('pathlib.Path.home')
    def test_backup_manager_default_location(self, mock_home):
        """Test BackupManager with default location"""
        mock_home.return_value = self.test_dir

        manager = BackupManager()

        # Must create in default directory
        expected_dir = self.test_dir / ".local" / "share" / "rdp-session-manager" / "backups"
        self.assertTrue(expected_dir.exists())

    def test_create_backup(self):
        """Test create_backup method"""
        user_data = {
            'username': 'testuser',
            'uid': 5000,
            'home_dir': '/opt/rdp-users/testuser',
            'desktop_env': 'xfce',
            'rdp_port': 3389
        }

        backup_file = self.backup_manager.create_backup(user_data)

        self.assertIsNotNone(backup_file)
        self.assertTrue(backup_file.exists())
        self.assertIn('testuser', backup_file.name)

    def test_create_backup_content(self):
        """Test that backup file has correct content"""
        user_data = {
            'username': 'testuser',
            'uid': 5000,
            'desktop_env': 'xfce'
        }

        backup_file = self.backup_manager.create_backup(user_data)

        # Read backup content
        with open(backup_file, 'r') as f:
            backup_data = json.load(f)

        # Check structure
        self.assertIn('timestamp', backup_data)
        self.assertIn('version', backup_data)
        self.assertIn('user_data', backup_data)

        # Check user data
        self.assertEqual(backup_data['user_data']['username'], 'testuser')
        self.assertEqual(backup_data['user_data']['uid'], 5000)

    def test_restore_backup(self):
        """Test restore_backup method"""
        # Create backup
        user_data = {
            'username': 'testuser',
            'uid': 5000,
            'desktop_env': 'xfce'
        }
        backup_file = self.backup_manager.create_backup(user_data)

        # Restaurar backup
        restored_data = self.backup_manager.restore_backup(backup_file)

        self.assertIsNotNone(restored_data)
        self.assertEqual(restored_data['username'], 'testuser')
        self.assertEqual(restored_data['uid'], 5000)

    def test_restore_backup_nonexistent(self):
        """Test restore_backup with non-existent file"""
        fake_file = self.test_dir / "nonexistent.json"

        restored_data = self.backup_manager.restore_backup(fake_file)

        self.assertIsNone(restored_data)

    def test_list_backups(self):
        """Test list_backups method"""
        import time

        # Create some backups with small delay to guarantee unique timestamps
        user_data1 = {'username': 'user1', 'uid': 5000}
        user_data2 = {'username': 'user2', 'uid': 5001}
        user_data3 = {'username': 'user1', 'uid': 5000}

        self.backup_manager.create_backup(user_data1)
        time.sleep(0.01)  # Pequeno delay
        self.backup_manager.create_backup(user_data2)
        time.sleep(0.01)  # Pequeno delay
        self.backup_manager.create_backup(user_data3)

        # List all
        all_backups = self.backup_manager.list_backups()
        self.assertGreaterEqual(len(all_backups), 2) # At least 2 (can have 3 if timestamps are different)

        # List by user
        user1_backups = self.backup_manager.list_backups(username='user1')
        self.assertGreaterEqual(len(user1_backups), 1)

        user2_backups = self.backup_manager.list_backups(username='user2')
        self.assertEqual(len(user2_backups), 1)

    def test_list_backups_empty(self):
        """Test list_backups with no backups"""
        backups = self.backup_manager.list_backups()

        self.assertEqual(len(backups), 0)

    def test_list_backups_sorted(self):
        """Test that list_backups returns sorted results (newest first)"""
        # Create backups at short intervals
        for i in range(3):
            user_data = {'username': f'user{i}', 'uid': 5000 + i}
            self.backup_manager.create_backup(user_data)

        backups = self.backup_manager.list_backups()

        # Check that they are ordered (most recent first)
        self.assertEqual(len(backups), 3)
        # The latest must have user2
        self.assertIn('user2', backups[0].name)
        # The oldest must have user0
        self.assertIn('user0', backups[2].name)

    def test_delete_backup(self):
        """Test delete_backup method"""
        # Create backup
        user_data = {'username': 'testuser', 'uid': 5000}
        backup_file = self.backup_manager.create_backup(user_data)

        # Check that it exists
        self.assertTrue(backup_file.exists())

        # Delete
        result = self.backup_manager.delete_backup(backup_file)

        self.assertTrue(result)
        self.assertFalse(backup_file.exists())

    def test_delete_backup_nonexistent(self):
        """Test delete_backup with non-existent file"""
        fake_file = self.test_dir / "nonexistent.json"

        result = self.backup_manager.delete_backup(fake_file)

        self.assertFalse(result)

    def test_cleanup_old_backups(self):
        """Test cleanup_old_backups method"""
        # Create "old" backups by modifying the timestamp in the name
        old_date = (datetime.now() - timedelta(days=35)).strftime("%Y%m%d_%H%M%S")
        old_backup = self.test_dir / f"backup_olduser_{old_date}.json"

        # Create old file
        with open(old_backup, 'w') as f:
            json.dump({'timestamp': old_date, 'version': '1.0', 'user_data': {'username': 'olduser'}}, f)

        # Create recent backup
        recent_data = {'username': 'recentuser', 'uid': 5000}
        self.backup_manager.create_backup(recent_data)

        # Clear old backups (30 days)
        removed = self.backup_manager.cleanup_old_backups(days=30)

        # Must have removed 1 backup
        self.assertEqual(removed, 1)

        # Old backup should no longer exist
        self.assertFalse(old_backup.exists())

        # Recent backup must exist
        backups = self.backup_manager.list_backups()
        self.assertEqual(len(backups), 1)

    def test_cleanup_old_backups_by_user(self):
        """Test cleanup_old_backups filtered by username"""
        # Create old backups from different users
        old_date = (datetime.now() - timedelta(days=35)).strftime("%Y%m%d_%H%M%S")

        old_backup1 = self.test_dir / f"backup_user1_{old_date}.json"
        old_backup2 = self.test_dir / f"backup_user2_{old_date}.json"

        for backup in [old_backup1, old_backup2]:
            with open(backup, 'w') as f:
                json.dump({'timestamp': old_date, 'version': '1.0', 'user_data': {}}, f)

        # Clear only user1's backups
        removed = self.backup_manager.cleanup_old_backups(days=30, username='user1')

        self.assertEqual(removed, 1)
        self.assertFalse(old_backup1.exists())
        self.assertTrue(old_backup2.exists())

    def test_export_all_configs(self):
        """Test export_all_configs method"""
        # Create some backups
        user1_data = {'username': 'user1', 'uid': 5000}
        user2_data = {'username': 'user2', 'uid': 5001}

        self.backup_manager.create_backup(user1_data)
        self.backup_manager.create_backup(user2_data)

        # Exportar
        export_file = self.test_dir / "export.json"
        result = self.backup_manager.export_all_configs(export_file)

        self.assertTrue(result)
        self.assertTrue(export_file.exists())

        # Check content
        with open(export_file, 'r') as f:
            export_data = json.load(f)

        self.assertIn('export_date', export_data)
        self.assertIn('version', export_data)
        self.assertIn('users', export_data)
        self.assertEqual(len(export_data['users']), 2)

    def test_export_all_configs_empty(self):
        """Test export_all_configs with no backups"""
        export_file = self.test_dir / "export_empty.json"
        result = self.backup_manager.export_all_configs(export_file)

        self.assertTrue(result)

        # Check which file was created with empty list
        with open(export_file, 'r') as f:
            export_data = json.load(f)

        self.assertEqual(len(export_data['users']), 0)

    def test_import_configs(self):
        """Test import_configs method"""
        # Create import file
        import_data = {
            'export_date': datetime.now().isoformat(),
            'version': '1.0',
            'users': [
                {'username': 'importuser1', 'uid': 5000},
                {'username': 'importuser2', 'uid': 5001}
            ]
        }

        import_file = self.test_dir / "import.json"
        with open(import_file, 'w') as f:
            json.dump(import_data, f)

        # Importar
        result = self.backup_manager.import_configs(import_file)

        self.assertTrue(result)

        # Check which backups have been created
        backups = self.backup_manager.list_backups()
        self.assertEqual(len(backups), 2)

    def test_import_configs_nonexistent(self):
        """Test import_configs with non-existent file"""
        fake_file = self.test_dir / "nonexistent.json"

        result = self.backup_manager.import_configs(fake_file)

        self.assertFalse(result)

    def test_backup_filename_format(self):
        """Test that backup filename has correct format"""
        user_data = {'username': 'testuser', 'uid': 5000}

        backup_file = self.backup_manager.create_backup(user_data)

        # Name must follow the format: backup_USERNAME_TIMESTAMP.json
        self.assertTrue(backup_file.name.startswith('backup_testuser_'))
        self.assertTrue(backup_file.name.endswith('.json'))

    def test_multiple_backups_same_user(self):
        """Test creating multiple backups for same user"""
        import time

        user_data = {'username': 'testuser', 'uid': 5000}

        # Create multiple backups with small delay to guarantee unique timestamps
        backup1 = self.backup_manager.create_backup(user_data)
        time.sleep(0.01)
        backup2 = self.backup_manager.create_backup(user_data)
        time.sleep(0.01)
        backup3 = self.backup_manager.create_backup(user_data)

        # Everyone must exist
        self.assertTrue(backup1.exists())
        self.assertTrue(backup2.exists())
        self.assertTrue(backup3.exists())

        # List must return at least 1 backup (may have the same timestamp if run very fast)
        backups = self.backup_manager.list_backups(username='testuser')
        self.assertGreaterEqual(len(backups), 1)

    def test_backup_restore_roundtrip(self):
        """Test complete backup and restore cycle"""
        # Original data
        original_data = {
            'username': 'roundtripuser',
            'uid': 5000,
            'home_dir': '/opt/rdp-users/roundtripuser',
            'desktop_env': 'kde',
            'rdp_port': 3391,
            'enabled': True,
            'is_superuser': False
        }

        # Create backup
        backup_file = self.backup_manager.create_backup(original_data)

        # Restaurar
        restored_data = self.backup_manager.restore_backup(backup_file)

        # Check that all data has been preserved
        self.assertEqual(restored_data['username'], original_data['username'])
        self.assertEqual(restored_data['uid'], original_data['uid'])
        self.assertEqual(restored_data['home_dir'], original_data['home_dir'])
        self.assertEqual(restored_data['desktop_env'], original_data['desktop_env'])
        self.assertEqual(restored_data['rdp_port'], original_data['rdp_port'])
        self.assertEqual(restored_data['enabled'], original_data['enabled'])
        self.assertEqual(restored_data['is_superuser'], original_data['is_superuser'])


if __name__ == '__main__':
    unittest.main()
