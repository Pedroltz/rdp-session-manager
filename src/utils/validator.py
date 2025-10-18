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
            return False, "Nome de usuário não pode ser vazio"

        if len(username) < 3:
            return False, "Nome de usuário muito curto (mínimo 3 caracteres)"

        if len(username) > 32:
            return False, "Nome de usuário muito longo (máximo 32 caracteres)"

        if not re.match(Validator.USERNAME_PATTERN, username):
            return False, "Nome de usuário inválido. Deve começar com letra minúscula e conter apenas letras, números, - e _"

        # Verificar nomes reservados
        reserved = ['root', 'admin', 'administrator', 'sudo', 'system', 'daemon']
        if username.lower() in reserved:
            return False, f"Nome '{username}' é reservado pelo sistema"

        return True, ""

    @staticmethod
    def validate_password(password: str, confirm_password: str = None) -> Tuple[bool, str]:
        """
        Valida senha

        Returns:
            Tuple (válido, mensagem_erro)
        """
        if not password:
            return False, "Senha não pode ser vazia"

        if len(password) < Validator.PASSWORD_MIN_LENGTH:
            return False, f"Senha muito curta (mínimo {Validator.PASSWORD_MIN_LENGTH} caracteres)"

        # Verificar complexidade
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)

        if not (has_upper and has_lower and has_digit):
            return False, "Senha deve conter letras maiúsculas, minúsculas e números"

        # Verificar confirmação
        if confirm_password is not None and password != confirm_password:
            return False, "Senhas não coincidem"

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
                return False, "Porta deve ser um número inteiro"

        if port < Validator.PORT_MIN:
            return False, f"Porta muito baixa (mínimo {Validator.PORT_MIN})"

        if port > Validator.PORT_MAX:
            return False, f"Porta muito alta (máximo {Validator.PORT_MAX})"

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
            return False, f"Ambiente desktop '{de}' não suportado. Opções: {', '.join(valid_des)}"

        return True, ""

    @staticmethod
    def validate_home_dir(home_dir: str) -> Tuple[bool, str]:
        """
        Valida diretório home

        Returns:
            Tuple (válido, mensagem_erro)
        """
        if not home_dir:
            return False, "Diretório home não pode ser vazio"

        if not home_dir.startswith('/'):
            return False, "Diretório home deve ser caminho absoluto"

        # Evitar diretórios sensíveis
        forbidden = ['/root', '/bin', '/sbin', '/usr/bin', '/usr/sbin', '/etc', '/sys', '/proc']
        if home_dir in forbidden or any(home_dir.startswith(f) for f in forbidden):
            return False, f"Diretório '{home_dir}' não é permitido"

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
