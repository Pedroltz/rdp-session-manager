#!/usr/bin/env python3
"""
Helper for integration with PolicyKit
Supports fallback to sudo in headless environments
or in environments where PolicyKit does not work (e.g. WSL)
"""

import subprocess
import logging
import os
import shutil
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)

# Global flag to force CLI mode (uses sudo instead of pkexec)
_force_cli_mode = False


def set_cli_mode(enabled: bool = True) -> None:
    """
    Sets CLI mode (headless), forcing the use of sudo instead of pkexec.

    Args:
        enabled: True to force sudo, False for automatic behavior
    """
    global _force_cli_mode
    _force_cli_mode = enabled
    if enabled:
        logger.debug("CLI mode enabled - forcing use of sudo")


def is_cli_mode() -> bool:
    """
    Checks whether CLI mode is active.

    Returns:
        True if CLI mode is forced, False otherwise
    """
    return _force_cli_mode


def is_wsl() -> bool:
    """
    Detects whether it is running on Windows Subsystem for Linux (WSL).

    PolicyKit does not work correctly in WSL because there is no agent
    authentication system running, even when there is a display available (WSLg).

    Returns:
        True if running on WSL, False otherwise
    """
    # Method 1: Check WSL_DISTRO_NAME environment variable
    if os.environ.get('WSL_DISTRO_NAME'):
        logger.debug("WSL detectado via WSL_DISTRO_NAME")
        return True

    # Method 2: Check /proc/version
    try:
        with open('/proc/version', 'r') as f:
            version = f.read().lower()
            if 'microsoft' in version or 'wsl' in version:
                logger.debug("WSL detectado via /proc/version")
                return True
    except (FileNotFoundError, PermissionError):
        pass

    # Method 3: Check existence of WSLInterop
    if os.path.exists('/proc/sys/fs/binfmt_misc/WSLInterop'):
        logger.debug("WSL detectado via WSLInterop")
        return True

    return False


def has_display() -> bool:
    """
    Detects whether a graphical environment (display) is available.

    Checks:
    - DISPLAY (X11)
    - WAYLAND_DISPLAY (Wayland)

    Returns:
        True if there is a graphical environment, False otherwise (headless)
    """
    display = os.environ.get('DISPLAY')
    wayland = os.environ.get('WAYLAND_DISPLAY')

    has_gui = bool(display or wayland)
    logger.debug(f"Display detection: DISPLAY={display}, WAYLAND_DISPLAY={wayland}, has_gui={has_gui}")

    return has_gui


def has_polkit_agent() -> bool:
    """
    Checks whether a PolicyKit agent is available for authentication.
    On headless servers, there is usually no graphics agent installed.
    In WSL, PolicyKit does not work even with display available.
    In CLI mode, always use sudo for better terminal experience.

    Returns:
        True if there is a PolicyKit agent, False otherwise
    """
    # Forced CLI mode - always use sudo
    if is_cli_mode():
        logger.debug("CLI mode active - using sudo")
        return False

    # Check if pkexec is available
    if not shutil.which('pkexec'):
        logger.debug("pkexec not found in PATH")
        return False

    # WSL does not support PolicyKit correctly (there is no authentication agent)
    if is_wsl():
        logger.debug("WSL detected - PolicyKit not working, using sudo")
        return False

    # If there is no display, there is no graphics agent
    if not has_display():
        logger.debug("No display - assuming no PolicyKit agent")
        return False

    return True


def get_privilege_command() -> Tuple[str, List[str]]:
    """
    Returns the appropriate command for elevation of privileges.

    In GUI environments: use pkexec (PolicyKit)
    In headless environments: use sudo

    Returns:
        Tuple (method_name, base_argument_list)
        Ex: ('pkexec', ['pkexec', '--user', 'root'])
        Ex: ('sudo', ['sudo'])
    """
    if has_polkit_agent():
        logger.debug("Using pkexec for elevation of privileges")
        return ('pkexec', ['pkexec', '--user', 'root'])
    else:
        logger.debug("Using sudo for elevation of privileges (headless environment)")
        return ('sudo', ['sudo'])


class PolicyKitHelper:
    """Helper to execute administrative commands via PolicyKit"""

    HELPER_PATH = "/usr/libexec/rdp-session-helper.py"

    @staticmethod
    def check_authorization(action_id: str) -> bool:
        """
        Checks whether the user is authorized for an action

        Args:
            action_id: PolicyKit action ID

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
        Execute command with privileges via PolicyKit or sudo (headless)

        Args:
            action_id: PolicyKit action ID
            command: Command and arguments

        Returns:
            Tuple (success, output, error)
        """
        try:
            # Get appropriate elevation command (pkexec or sudo)
            method, base_cmd = get_privilege_command()
            full_command = base_cmd + command

            logger.debug(f"Running with {method}: {' '.join(full_command)}")

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
            error_msg = f"Error executing command: {e}"
            logger.error(error_msg)
            return False, "", error_msg

    @staticmethod
    def call_helper(action: str, **kwargs) -> tuple:
        """
        Call the helper script with PolicyKit

        Args:
            action: Action to execute (create-user, delete-user, etc.)
            **kwargs: Action arguments

        Returns:
            Tuple (success, result)
        """
        import json

        try:
            # Prepare arguments
            args = json.dumps({
                'action': action,
                **kwargs
            })

            # Run helper
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
            logger.error(f"Error when calling helper: {e}")
            return False, {'error': str(e)}
