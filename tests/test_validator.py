#!/usr/bin/env python3
"""
Tests for Validator module
"""

import unittest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.validator import Validator


class TestValidator(unittest.TestCase):
    """Test Validator class"""

    def test_validate_username_valid(self):
        """Test valid usernames"""
        valid_usernames = [
            'user123',
            'testuser',
            'john_doe',
            'user-name',
            'abc'
        ]

        for username in valid_usernames:
            valid, error = Validator.validate_username(username)
            self.assertTrue(valid, f"Username '{username}' should be valid")

    def test_validate_username_invalid(self):
        """Test invalid usernames"""
        invalid_usernames = [
            '',  # Empty
            'ab',  # Too short
            '123user',  # Starts with number
            'User',  # Uppercase
            'user name',  # Space
            'root',  # Reserved
            'a' * 33  # Too long
        ]

        for username in invalid_usernames:
            valid, error = Validator.validate_username(username)
            self.assertFalse(valid, f"Username '{username}' should be invalid")

    def test_validate_password_valid(self):
        """Test valid passwords"""
        valid_passwords = [
            ('Password123', 'Password123'),
            ('MyP@ssw0rd', 'MyP@ssw0rd'),
            ('Abcdef12', 'Abcdef12'),
        ]

        for password, confirm in valid_passwords:
            valid, error = Validator.validate_password(password, confirm)
            self.assertTrue(valid, f"Password should be valid: {error}")

    def test_validate_password_invalid(self):
        """Test invalid passwords"""
        invalid_cases = [
            ('', ''),  # Empty
            ('short', 'short'),  # Too short
            ('password', 'password'),  # No uppercase or numbers
            ('PASSWORD', 'PASSWORD'),  # No lowercase
            ('Password', 'Password'),  # No numbers
            ('Password123', 'Different123'),  # Mismatch
        ]

        for password, confirm in invalid_cases:
            valid, error = Validator.validate_password(password, confirm)
            self.assertFalse(valid, "Password should be invalid")

    def test_validate_port_valid(self):
        """Test valid ports"""
        valid_ports = [1024, 3389, 8080, 65535]

        for port in valid_ports:
            valid, error = Validator.validate_port(port)
            self.assertTrue(valid, f"Port {port} should be valid")

    def test_validate_port_invalid(self):
        """Test invalid ports"""
        invalid_ports = [0, 80, 1023, 65536, 100000, 'abc']

        for port in invalid_ports:
            valid, error = Validator.validate_port(port)
            self.assertFalse(valid, f"Port {port} should be invalid")

    def test_sanitize_username(self):
        """Test username sanitization"""
        test_cases = [
            ('User123', 'user123'),
            ('123user', 'u123user'),
            ('user@name', 'username'),
            ('CAPS', 'caps'),
        ]

        for input_val, expected in test_cases:
            result = Validator.sanitize_username(input_val)
            self.assertEqual(result, expected)

    def test_sanitize_username_length_limit(self):
        """Test username sanitization with length limit"""
        # 40 caracteres devem ser truncados para 32
        long_username = 'a' * 40
        result = Validator.sanitize_username(long_username)
        self.assertEqual(len(result), 32)

    def test_validate_desktop_env_valid(self):
        """Test valid desktop environments"""
        valid_des = ['gnome', 'xfce', 'kde']

        for de in valid_des:
            valid, error = Validator.validate_desktop_env(de)
            self.assertTrue(valid, f"DE '{de}' should be valid")
            self.assertEqual(error, "")

    def test_validate_desktop_env_invalid(self):
        """Test invalid desktop environments"""
        invalid_des = [
            'windows', 'macos', 'unity', 'invalid',
            'mate', 'cinnamon', 'lxde', 'lxqt', 'plasma', 'xfce4'
        ]

        for de in invalid_des:
            valid, error = Validator.validate_desktop_env(de)
            self.assertFalse(valid, f"DE '{de}' should be invalid")
            self.assertNotEqual(error, "")

    def test_validate_desktop_env_case_insensitive(self):
        """Test desktop environment validation is case insensitive"""
        valid, error = Validator.validate_desktop_env('GNOME')
        self.assertTrue(valid)

        valid, error = Validator.validate_desktop_env('Xfce')
        self.assertTrue(valid)

    def test_validate_home_dir_valid(self):
        """Test valid home directories"""
        valid_homes = [
            '/home/testuser',
            '/opt/rdp-users/testuser',
            '/var/rdp/testuser',
        ]

        for home in valid_homes:
            valid, error = Validator.validate_home_dir(home)
            self.assertTrue(valid, f"Home '{home}' should be valid: {error}")

    def test_validate_home_dir_invalid(self):
        """Test invalid home directories"""
        invalid_cases = [
            ('', 'empty'),
            ('relative/path', 'not absolute'),
            ('/root', 'forbidden'),
            ('/etc/passwd', 'forbidden'),
            ('/usr/bin/test', 'forbidden'),
        ]

        for home, reason in invalid_cases:
            valid, error = Validator.validate_home_dir(home)
            self.assertFalse(valid, f"Home '{home}' should be invalid ({reason})")
            self.assertNotEqual(error, "")

    def test_sanitize_path(self):
        """Test path sanitization"""
        test_cases = [
            ('/home/user/../etc', '/home/user/etc'),
            ('/tmp/file;rm -rf /', '/tmp/filerm -rf /'),
            ('/path/with/$VAR', '/path/with/VAR'),
            ('/path/with`command`', '/path/withcommand'),
            ('/normal/path', '/normal/path'),
        ]

        for input_path, expected in test_cases:
            result = Validator.sanitize_path(input_path)
            # Verificar que caracteres perigosos foram removidos
            self.assertNotIn('..', result)
            self.assertNotIn('$', result)
            self.assertNotIn('`', result)
            self.assertNotIn(';', result)

    def test_validate_username_reserved_names(self):
        """Test that reserved usernames are rejected"""
        reserved_names = ['root', 'admin', 'administrator', 'sudo', 'system', 'daemon']

        for name in reserved_names:
            valid, error = Validator.validate_username(name)
            self.assertFalse(valid, f"Reserved name '{name}' should be invalid")
            self.assertIn('reserved', error.lower())

    def test_validate_password_complexity(self):
        """Test password complexity requirements"""
        # Apenas minúsculas - inválido
        valid, error = Validator.validate_password('password', 'password')
        self.assertFalse(valid)

        # Apenas maiúsculas - inválido
        valid, error = Validator.validate_password('PASSWORD', 'PASSWORD')
        self.assertFalse(valid)

        # Sem números - inválido
        valid, error = Validator.validate_password('Password', 'Password')
        self.assertFalse(valid)

        # Tudo correto
        valid, error = Validator.validate_password('Password123', 'Password123')
        self.assertTrue(valid)

    def test_validate_password_without_confirmation(self):
        """Test password validation without confirmation"""
        # Senha válida sem confirmação
        valid, error = Validator.validate_password('ValidPass123')
        self.assertTrue(valid, f"Password should be valid: {error}")

    def test_validate_port_string_conversion(self):
        """Test port validation with string input"""
        # String válida deve ser convertida
        valid, error = Validator.validate_port('3389')
        self.assertTrue(valid)

        # String inválida
        valid, error = Validator.validate_port('not_a_number')
        self.assertFalse(valid)

    def test_validate_port_boundary_values(self):
        """Test port validation with boundary values"""
        # Limite inferior válido
        valid, error = Validator.validate_port(1024)
        self.assertTrue(valid)

        # Limite superior válido
        valid, error = Validator.validate_port(65535)
        self.assertTrue(valid)

        # Abaixo do limite
        valid, error = Validator.validate_port(1023)
        self.assertFalse(valid)

        # Acima do limite
        valid, error = Validator.validate_port(65536)
        self.assertFalse(valid)


if __name__ == '__main__':
    unittest.main()
