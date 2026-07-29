#!/usr/bin/env python3
"""
Helper para integração com PolicyKit
Suporta fallback para sudo em ambientes sem interface gráfica (headless)
ou em ambientes onde PolicyKit não funciona (ex: WSL)
"""

import subprocess
import logging
import os
import shutil
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Flag global para forçar modo CLI (usa sudo ao invés de pkexec)
_force_cli_mode = False


def set_cli_mode(enabled: bool = True) -> None:
    """
    Define o modo CLI (headless), forçando o uso de sudo ao invés de pkexec.

    Args:
        enabled: True para forçar sudo, False para comportamento automático
    """
    global _force_cli_mode
    _force_cli_mode = enabled
    if enabled:
        logger.debug("CLI mode enabled—forcing sudo")


def is_cli_mode() -> bool:
    """
    Verifica se o modo CLI está ativo.

    Returns:
        True se modo CLI está forçado, False caso contrário
    """
    return _force_cli_mode


def is_wsl() -> bool:
    """
    Detecta se está rodando no Windows Subsystem for Linux (WSL).

    PolicyKit não funciona corretamente no WSL porque não há um agente
    de autenticação rodando, mesmo quando há um display disponível (WSLg).

    Returns:
        True se estiver rodando no WSL, False caso contrário
    """
    # Método 1: Verificar variável de ambiente WSL_DISTRO_NAME
    if os.environ.get('WSL_DISTRO_NAME'):
        logger.debug("WSL detectado via WSL_DISTRO_NAME")
        return True

    # Método 2: Verificar /proc/version
    try:
        with open('/proc/version', 'r') as f:
            version = f.read().lower()
            if 'microsoft' in version or 'wsl' in version:
                logger.debug("WSL detectado via /proc/version")
                return True
    except (FileNotFoundError, PermissionError):
        pass

    # Método 3: Verificar existência do WSLInterop
    if os.path.exists('/proc/sys/fs/binfmt_misc/WSLInterop'):
        logger.debug("WSL detectado via WSLInterop")
        return True

    return False


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
    No WSL, PolicyKit não funciona mesmo com display disponível.
    No modo CLI, sempre usa sudo para melhor experiência no terminal.

    Returns:
        True se há agente PolicyKit, False caso contrário
    """
    # Modo CLI forçado - sempre usar sudo
    if is_cli_mode():
        logger.debug("CLI mode active—using sudo")
        return False

    # Verificar se pkexec está disponível
    if not shutil.which('pkexec'):
        logger.debug("pkexec not found in PATH")
        return False

    # WSL não suporta PolicyKit corretamente (não há agente de autenticação)
    if is_wsl():
        logger.debug("WSL detected—PolicyKit is unavailable; using sudo")
        return False

    # Se não há display, não há agente gráfico
    if not has_display():
        logger.debug("No display—assuming no PolicyKit agent is available")
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
        logger.debug("Using pkexec for privilege elevation")
        return ('pkexec', ['pkexec', '--user', 'root'])
    else:
        logger.debug("Using sudo for privilege elevation (headless environment)")
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
            logger.error(f"Error checking authorization: {e}")
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
            error_msg = "Command timed out"
            logger.error(error_msg)
            return False, "", error_msg

        except Exception as e:
            error_msg = f"Error running command: {e}"
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
            logger.error(f"Error calling helper: {e}")
            return False, {'error': str(e)}
