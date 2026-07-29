#!/usr/bin/env python3
"""
Tests for AppConfig module
"""

import unittest
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.config import AppConfig


class TestAppConfig(unittest.TestCase):
    """Test AppConfig class"""

    def setUp(self):
        """Setup test fixtures"""
        # Create temporary directory for testing
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / '.config' / 'rdp-session-manager'
        self.config_file = self.config_dir / 'config.ini'

    def tearDown(self):
        """Cleanup test fixtures"""
        # Remove temporary directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @patch('pathlib.Path.home')
    def test_config_initialization(self, mock_home):
        """Test AppConfig initialization"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        self.assertIsNotNone(config)
        self.assertTrue(config.config_dir.exists())
        self.assertTrue(config.config_file.exists())

    @patch('pathlib.Path.home')
    def test_config_default_values(self, mock_home):
        """Test AppConfig default values"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Check default port
        default_port = config.get_default_rdp_port()
        self.assertEqual(default_port, 3389)

    @patch('pathlib.Path.home')
    def test_config_file_creation(self, mock_home):
        """Test that config file is created with defaults"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # File must exist
        self.assertTrue(config.config_file.exists())

        # Check content
        content = config.config_file.read_text()
        self.assertIn('[rdp]', content)
        self.assertIn('default_port', content)

    @patch('pathlib.Path.home')
    def test_get_default_rdp_port(self, mock_home):
        """Test get_default_rdp_port method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        port = config.get_default_rdp_port()

        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 1)
        self.assertLessEqual(port, 65535)

    @patch('pathlib.Path.home')
    def test_set_default_rdp_port(self, mock_home):
        """Test set_default_rdp_port method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Set new port
        result = config.set_default_rdp_port(8080)
        self.assertTrue(result)

        # Check if it was saved
        port = config.get_default_rdp_port()
        self.assertEqual(port, 8080)

    @patch('pathlib.Path.home')
    def test_set_default_rdp_port_invalid(self, mock_home):
        """Test set_default_rdp_port with invalid port"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Invalid port (too low)
        result = config.set_default_rdp_port(0)
        self.assertFalse(result)

        # Invalid port (too high)
        result = config.set_default_rdp_port(70000)
        self.assertFalse(result)

        # Invalid port (negative)
        result = config.set_default_rdp_port(-1)
        self.assertFalse(result)

    @patch('pathlib.Path.home')
    def test_get_default_rdp_port_invalid_fallback(self, mock_home):
        """Test get_default_rdp_port fallback for invalid stored port"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Set invalid port manually in file
        config.config.set('rdp', 'default_port', '999999')
        config._save()

        # Should return 3389 as fallback
        port = config.get_default_rdp_port()
        self.assertEqual(port, 3389)

    @patch('pathlib.Path.home')
    def test_get_generic_value(self, mock_home):
        """Test generic get method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Get default value
        value = config.get('rdp', 'default_port')
        self.assertEqual(value, '3389')

        # Get non-existent value with fallback
        value = config.get('nonexistent', 'key', fallback='default_value')
        self.assertEqual(value, 'default_value')

    @patch('pathlib.Path.home')
    def test_set_generic_value(self, mock_home):
        """Test generic set method"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Set new value
        result = config.set('custom', 'setting', 'test_value')
        self.assertTrue(result)

        # Check if it was saved
        value = config.get('custom', 'setting')
        self.assertEqual(value, 'test_value')

    @patch('pathlib.Path.home')
    def test_set_creates_section(self, mock_home):
        """Test that set creates section if it doesn't exist"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Set value in non-existent section
        result = config.set('newsection', 'key', 'value')
        self.assertTrue(result)

        # Check which section was created
        self.assertTrue(config.config.has_section('newsection'))

        # Check value
        value = config.get('newsection', 'key')
        self.assertEqual(value, 'value')

    @patch('pathlib.Path.home')
    def test_config_persistence(self, mock_home):
        """Test that config persists across instances"""
        mock_home.return_value = self.test_dir

        # First instance
        config1 = AppConfig()
        config1.set_default_rdp_port(5000)

        # Second instance (must load from file)
        config2 = AppConfig()
        port = config2.get_default_rdp_port()

        self.assertEqual(port, 5000)

    @patch('pathlib.Path.home')
    def test_config_load_existing(self, mock_home):
        """Test loading existing config file"""
        mock_home.return_value = self.test_dir

        # Create first instance
        config1 = AppConfig()
        config1.set('test', 'key', 'value')

        # Create second instance (must load existing file)
        config2 = AppConfig()
        value = config2.get('test', 'key')

        self.assertEqual(value, 'value')

    @patch('pathlib.Path.home')
    def test_config_ensures_defaults(self, mock_home):
        """Test that missing default sections/keys are added"""
        mock_home.return_value = self.test_dir

        # Create config without some defaults
        config_dir = self.test_dir / '.config' / 'rdp-session-manager'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'config.ini'

        # Create incomplete file
        config_file.write_text('[other]\nkey=value\n')

        # Load config (must add defaults)
        config = AppConfig()

        # Check which defaults have been added
        self.assertTrue(config.config.has_section('rdp'))
        self.assertTrue(config.config.has_option('rdp', 'default_port'))

    @patch('pathlib.Path.home')
    def test_config_invalid_file_recreates(self, mock_home):
        """Test that invalid config file is recreated"""
        mock_home.return_value = self.test_dir

        config_dir = self.test_dir / '.config' / 'rdp-session-manager'
        config_dir.mkdir(parents=True, exist_ok=True)
        config_file = config_dir / 'config.ini'

        # Create invalid file
        config_file.write_text('invalid config content [[[')

        # Load config (must recreate with defaults)
        config = AppConfig()

        # Must have default values
        port = config.get_default_rdp_port()
        self.assertEqual(port, 3389)

    @patch('pathlib.Path.home')
    def test_config_multiple_sections(self, mock_home):
        """Test config with multiple sections"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Add values ​​in multiple sections
        config.set('section1', 'key1', 'value1')
        config.set('section2', 'key2', 'value2')
        config.set('section3', 'key3', 'value3')

        # Check all values
        self.assertEqual(config.get('section1', 'key1'), 'value1')
        self.assertEqual(config.get('section2', 'key2'), 'value2')
        self.assertEqual(config.get('section3', 'key3'), 'value3')

    @patch('pathlib.Path.home')
    def test_config_overwrite_value(self, mock_home):
        """Test overwriting existing config value"""
        mock_home.return_value = self.test_dir

        config = AppConfig()

        # Set initial value
        config.set('test', 'key', 'value1')
        self.assertEqual(config.get('test', 'key'), 'value1')

        # Sobrescrever
        config.set('test', 'key', 'value2')
        self.assertEqual(config.get('test', 'key'), 'value2')


if __name__ == '__main__':
    unittest.main()
