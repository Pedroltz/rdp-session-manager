#!/usr/bin/env python3
"""
Input validation and sanitization module
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class Validator:
    """Data entry validator"""

    # Validation standards
    USERNAME_PATTERN = r'^[a-z][a-z0-9_-]{2,31}$'
    PASSWORD_MIN_LENGTH = 8
    PORT_MIN = 1024
    PORT_MAX = 65535

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Validate username

        Returns:
            Tuple (valid, error_message)
        """
        if not username:
            return False, "Username cannot be empty"

        if len(username) < 3:
            return False, "Username too short (minimum 3 characters)"

        if len(username) > 32:
            return False, "Username too long (maximum 32 characters)"

        if not re.match(Validator.USERNAME_PATTERN, username):
            return False, "Invalid username. Must start with a lowercase letter and contain only letters, numbers, - and _"

        # Check reserved names
        reserved = ['root', 'admin', 'administrator', 'sudo', 'system', 'daemon']
        if username.lower() in reserved:
            return False, f"Name '{username}' is reserved by the system"

        return True, ""

    @staticmethod
    def validate_password(password: str, confirm_password: str = None) -> Tuple[bool, str]:
        """
        Validate password

        Returns:
            Tuple (valid, error_message)
        """
        if not password:
            return False, "Password cannot be empty"

        if len(password) < Validator.PASSWORD_MIN_LENGTH:
            return False, f"Password too short (minimum {Validator.PASSWORD_MIN_LENGTH} characters)"

        # Check complexity
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase letters, lowercase letters and numbers"

        # Check confirmation
        if confirm_password is not None and password != confirm_password:
            return False, "Passwords do not match"

        return True, ""

    @staticmethod
    def validate_port(port: int) -> Tuple[bool, str]:
        """
        Validate port number

        Returns:
            Tuple (valid, error_message)
        """
        if not isinstance(port, int):
            try:
                port = int(port)
            except (ValueError, TypeError):
                return False, "Port must be an integer"

        if port < Validator.PORT_MIN:
            return False, f"Port too low (minimum {Validator.PORT_MIN})"

        if port > Validator.PORT_MAX:
            return False, f"Port too high (maximum {Validator.PORT_MAX})"

        return True, ""

    @staticmethod
    def validate_desktop_env(de: str) -> Tuple[bool, str]:
        """
        Validates desktop environment

        Returns:
            Tuple (valid, error_message)
        """
        valid_des = ['gnome', 'xfce', 'xfce4', 'kde', 'plasma', 'mate', 'cinnamon', 'lxde', 'lxqt']

        if de.lower() not in valid_des:
            return False, f"Desktop environment '{de}' not supported. Options: {', '.join(valid_des)}"

        return True, ""

    @staticmethod
    def validate_home_dir(home_dir: str) -> Tuple[bool, str]:
        """
        Validates home directory

        Returns:
            Tuple (valid, error_message)
        """
        if not home_dir:
            return False, "Home directory cannot be empty"

        if not home_dir.startswith('/'):
            return False, "Home directory must be absolute path"

        # Avoid sensitive directories
        forbidden = ['/root', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/etc', '/sys', '/proc']
        if home_dir in forbidden or any(home_dir.startswith(f) for f in forbidden):
            return False, f"Directory '{home_dir}' is not allowed"

        return True, ""

    @staticmethod
    def sanitize_username(username: str) -> str:
        """Remove invalid characters from username"""
        # Remove disallowed characters
        sanitized = re.sub(r'[^a-z0-9_-]', '', username.lower())

        # Make sure it starts with a letter
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'u' + sanitized

        return sanitized[:32] # Limit size

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Sanitizes file/directory path"""
        # Remove dangerous characters
        dangerous = ['..', '~', '$', '`', ';', '|', '&', '>', '<']

        for char in dangerous:
            path = path.replace(char, '')

        return path.strip()
