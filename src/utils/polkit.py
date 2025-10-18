#!/usr/bin/env python3
"""
Helper para integração com PolicyKit
"""

import subprocess
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class PolicyKitHelper:
    """Helper para executar comandos administrativos via PolicyKit"""

    HELPER_PATH = "/usr/libexec/rdp-session-helper.py"

    @staticmethod
    def check_authorization(action_id: str) -> bool:
        """
        Verifica se o usuário tem autorização para uma ação

        Args:
            action_id: ID da ação PolicyKit

        Returns:
            True se autorizado
        """
        try:
            result = subprocess.run(
                ['pkcheck', '--action-id', action_id, '--process', str(subprocess.os.getpid())],
                capture_output=True,
                text=True,
                timeout=30
            )

            return result.returncode == 0

        except Exception as e:
            logger.error(f"Erro ao verificar autorização: {e}")
            return False

    @staticmethod
    def execute_with_polkit(action_id: str, command: List[str]) -> tuple:
        """
        Executa comando com privilégios via PolicyKit

        Args:
            action_id: ID da ação PolicyKit
            command: Comando e argumentos

        Returns:
            Tuple (success, output, error)
        """
        try:
            # Usar pkexec para executar comando
            full_command = ['pkexec', '--user', 'root'] + command

            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutos timeout
            )

            success = result.returncode == 0
            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            error_msg = "Comando expirou (timeout)"
            logger.error(error_msg)
            return False, "", error_msg

        except Exception as e:
            error_msg = f"Erro ao executar comando: {e}"
            logger.error(error_msg)
            return False, "", error_msg

    @staticmethod
    def call_helper(action: str, **kwargs) -> tuple:
        """
        Chama o script helper com PolicyKit

        Args:
            action: Ação a executar (create-user, delete-user, etc)
            **kwargs: Argumentos da ação

        Returns:
            Tuple (success, result)
        """
        import json

        try:
            # Preparar argumentos
            args = json.dumps({
                'action': action,
                **kwargs
            })

            # Executar helper
            success, output, error = PolicyKitHelper.execute_with_polkit(
                f'com.rdp.SessionManager.{action}',
                [PolicyKitHelper.HELPER_PATH, args]
            )

            if success:
                try:
                    result = json.loads(output) if output else {}
                    return True, result
                except json.JSONDecodeError:
                    return True, {'output': output}
            else:
                return False, {'error': error}

        except Exception as e:
            logger.error(f"Erro ao chamar helper: {e}")
            return False, {'error': str(e)}
