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


if __name__ == '__main__':
    unittest.main()
