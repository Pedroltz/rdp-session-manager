#!/usr/bin/env python3
"""
Helper para integração com PolicyKit
Suporta fallback para sudo em ambientes sem interface gráfica (headless)
"""

import subprocess
import logging
import os
import shutil
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


def has_display() -> bool:
    """
    Detecta se há um ambiente gráfico (display) disponível.

    Verifica:
    - DISPLAY (X11)
    - WAYLAND_DISPLAY (Wayland)

    Returns:
        True se há ambiente gráfico, False caso contrário (headless)
    """
    display = os.environ.get('DISPLAY')
    wayland = os.environ.get('WAYLAND_DISPLAY')

    has_gui = bool(display or wayland)
    logger.debug(f"Display detection: DISPLAY={display}, WAYLAND_DISPLAY={wayland}, has_gui={has_gui}")

    return has_gui


def has_polkit_agent() -> bool:
    """
    Verifica se há um agente PolicyKit disponível para autenticação.
    Em servidores headless, geralmente não há agente gráfico instalado.

    Returns:
        True se há agente PolicyKit, False caso contrário
    """
    # Verificar se pkexec está disponível
    if not shutil.which('pkexec'):
        logger.debug("pkexec não encontrado no PATH")
        return False

    # Se não há display, não há agente gráfico
    if not has_display():
        logger.debug("Sem display - assumindo que não há agente PolicyKit")
        return False

    return True


def get_privilege_command() -> Tuple[str, List[str]]:
    """
    Retorna o comando apropriado para elevação de privilégios.

    Em ambientes com GUI: usa pkexec (PolicyKit)
    Em ambientes headless: usa sudo

    Returns:
        Tuple (nome_do_método, lista_de_argumentos_base)
        Ex: ('pkexec', ['pkexec', '--user', 'root'])
        Ex: ('sudo', ['sudo'])
    """
    if has_polkit_agent():
        logger.debug("Usando pkexec para elevação de privilégios")
        return ('pkexec', ['pkexec', '--user', 'root'])
    else:
        logger.debug("Usando sudo para elevação de privilégios (ambiente headless)")
        return ('sudo', ['sudo'])


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
        Executa comando com privilégios via PolicyKit ou sudo (em headless)

        Args:
            action_id: ID da ação PolicyKit
            command: Comando e argumentos

        Returns:
            Tuple (success, output, error)
        """
        try:
            # Obter comando de elevação apropriado (pkexec ou sudo)
            method, base_cmd = get_privilege_command()
            full_command = base_cmd + command

            logger.debug(f"Executando com {method}: {' '.join(full_command)}")

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
