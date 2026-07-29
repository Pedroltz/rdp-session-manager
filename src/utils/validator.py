#!/usr/bin/env python3
"""
Módulo de validação e sanitização de entrada
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)


class Validator:
    """Validador de entrada de dados"""

    # Padrões de validação
    USERNAME_PATTERN = r'^[a-z][a-z0-9_-]{2,31}$'
    PASSWORD_MIN_LENGTH = 8
    PORT_MIN = 1024
    PORT_MAX = 65535

    @staticmethod
    def validate_username(username: str) -> Tuple[bool, str]:
        """
        Valida nome de usuário

        Returns:
            Tuple (válido, mensagem_erro)
        """
        if not username:
            return False, "Username cannot be empty"

        if len(username) < 3:
            return False, "Username is too short (minimum 3 characters)"

        if len(username) > 32:
            return False, "Username is too long (maximum 32 characters)"

        if not re.match(Validator.USERNAME_PATTERN, username):
            return False, "Invalid username. It must start with a lowercase letter and contain only letters, numbers, hyphens, and underscores"

        # Verificar nomes reservados
        reserved = ['root', 'admin', 'administrator', 'sudo', 'system', 'daemon']
        if username.lower() in reserved:
            return False, f"The name '{username}' is reserved by the system"

        return True, ""

    @staticmethod
    def validate_password(password: str, confirm_password: str = None) -> Tuple[bool, str]:
        """
        Valida senha

        Returns:
            Tuple (válido, mensagem_erro)
        """
        if not password:
            return False, "Password cannot be empty"

        if len(password) < Validator.PASSWORD_MIN_LENGTH:
            return False, f"Password is too short (minimum {Validator.PASSWORD_MIN_LENGTH} characters)"

        # Verificar complexidade
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Password must contain uppercase letters, lowercase letters, and numbers"

        # Verificar confirmação
        if confirm_password is not None and password != confirm_password:
            return False, "Passwords do not match"

        return True, ""

    @staticmethod
    def validate_port(port: int) -> Tuple[bool, str]:
        """
        Valida número de porta

        Returns:
            Tuple (válido, mensagem_erro)
        """
        if not isinstance(port, int):
            try:
                port = int(port)
            except (ValueError, TypeError):
                return False, "Port must be an integer"

        if port < Validator.PORT_MIN:
            return False, f"Port is too low (minimum {Validator.PORT_MIN})"

        if port > Validator.PORT_MAX:
            return False, f"Port is too high (maximum {Validator.PORT_MAX})"

        return True, ""

    @staticmethod
    def validate_desktop_env(de: str) -> Tuple[bool, str]:
        """
        Valida ambiente desktop

        Returns:
            Tuple (válido, mensagem_erro)
        """
        valid_des = ['gnome', 'xfce', 'xfce4', 'kde', 'plasma', 'mate', 'cinnamon', 'lxde', 'lxqt']

        if de.lower() not in valid_des:
            return False, f"Unsupported desktop environment '{de}'. Options: {', '.join(valid_des)}"

        return True, ""

    @staticmethod
    def validate_home_dir(home_dir: str) -> Tuple[bool, str]:
        """
        Valida diretório home

        Returns:
            Tuple (válido, mensagem_erro)
        """
        if not home_dir:
            return False, "Home directory cannot be empty"

        if not home_dir.startswith('/'):
            return False, "Home directory must be an absolute path"

        # Evitar diretórios sensíveis
        forbidden = ['/root', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/etc', '/sys', '/proc']
        if home_dir in forbidden or any(home_dir.startswith(f) for f in forbidden):
            return False, f"Directory '{home_dir}' is not allowed"

        return True, ""

    @staticmethod
    def sanitize_username(username: str) -> str:
        """Remove caracteres inválidos do nome de usuário"""
        # Remover caracteres não permitidos
        sanitized = re.sub(r'[^a-z0-9_-]', '', username.lower())

        # Garantir que começa com letra
        if sanitized and not sanitized[0].isalpha():
            sanitized = 'u' + sanitized

        return sanitized[:32]  # Limitar tamanho

    @staticmethod
    def sanitize_path(path: str) -> str:
        """Sanitiza caminho de arquivo/diretório"""
        # Remover caracteres perigosos
        dangerous = ['..', '~', '$', '`', ';', '|', '&', '>', '<']

        for char in dangerous:
            path = path.replace(char, '')

        return path.strip()
