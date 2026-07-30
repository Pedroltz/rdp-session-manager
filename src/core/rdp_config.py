#!/usr/bin/env python3
"""
Módulo de configuração RDP
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

from core.desktop_environments import get_startup_command, normalize_desktop_id

logger = logging.getLogger(__name__)


class RDPConfig:
    """Gerenciador de configurações RDP (xrdp)"""

    def __init__(self):
        pass

    def create_user_session(self, username: str, uid: int, desktop_env: str,
                          rdp_port: int = 3389) -> bool:
        """
        Cria configuração de sessão RDP para um usuário

        Args:
            username: Nome do usuário
            uid: UID do usuário
            desktop_env: Ambiente desktop (gnome, xfce, kde)
            rdp_port: Porta RDP

        Returns:
            True se sucesso, False se falha
        """
        logger.info("=" * 70)
        logger.info("RDP_CONFIG: create_user_session() called")
        logger.info(f"  - Username: {username}")
        logger.info(f"  - UID: {uid}")
        logger.info(f"  - Desktop ENV: {desktop_env}")
        logger.info(f"  - RDP Port: {rdp_port}")
        logger.info("=" * 70)

        try:
            # Configurar xrdp
            logger.info("RDP_CONFIG: Generating xrdp session configuration...")
            session_config = self._generate_xrdp_session_config(
                username, desktop_env, rdp_port
            )
            logger.info(f"RDP_CONFIG: Start command: {session_config['start_command']}")

            # Determinar home directory
            home_dir = f"/opt/rdp-users/{username}"
            logger.info(f"RDP_CONFIG: Home directory: {home_dir}")

            # Criar script .xsession
            de_command = session_config['start_command']
            logger.info(f"RDP_CONFIG: Creating .xsession file with command: {de_command}")

            success = self._create_session_startup_script(username, de_command, home_dir)

            if not success:
                logger.error(f"RDP_CONFIG: ERROR - Failed to create .xsession script for {username}")
                return False

            logger.info("=" * 70)
            logger.info(f"RDP_CONFIG: SUCCESS - RDP configuration created for {username}")
            logger.info(f"  - Port: {rdp_port}")
            logger.info(f"  - .xsession file created at: {home_dir}/.xsession")
            logger.info("=" * 70)
            return True

        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"RDP_CONFIG: ERROR creating RDP configuration for {username}")
            logger.error(f"  - Exception: {type(e).__name__}")
            logger.error(f"  - Mensagem: {e}")
            logger.error("=" * 70)
            return False

    def _generate_xrdp_session_config(self, username: str, desktop_env: str,
                                     rdp_port: int) -> Dict:
        """Gera configuração de sessão xrdp"""

        desktop_env = normalize_desktop_id(desktop_env)
        de_command = get_startup_command(desktop_env)
        if de_command is None:
            raise ValueError(f"Unsupported desktop environment '{desktop_env}'")

        config = {
            'session_name': f"{username}_session",
            'username': username,
            'port': rdp_port,
            'desktop_env': desktop_env,
            'start_command': de_command,
        }

        return config


    def _create_session_startup_script(self, username: str, de_command: str,
                                      home_dir: str) -> bool:
        """Verifica se script de inicialização da sessão existe (.xsession)"""
        logger.info(f"RDP_CONFIG: Checking .xsession script for {username}...")
        logger.info(f"RDP_CONFIG:   - Home: {home_dir}")
        logger.info(f"RDP_CONFIG:   - DE command: {de_command}")

        try:
            # O arquivo .xsession já deve ter sido criado pelo user_manager durante create_user
            # Apenas verificar se existe
            xsession_path = Path(home_dir) / ".xsession"

            if xsession_path.exists():
                logger.info("RDP_CONFIG: OK .xsession script already exists")
                logger.info(f"RDP_CONFIG:   - File: {xsession_path}")
                return True
            else:
                logger.warning("RDP_CONFIG: WARNING .xsession script not found")
                logger.warning("RDP_CONFIG:   - This may indicate a problem during user creation")
                logger.warning("RDP_CONFIG:   - The file should have been created automatically")
                return False

        except Exception as e:
            logger.error("RDP_CONFIG: EXCEPTION while checking startup script")
            logger.error(f"RDP_CONFIG:   - Tipo: {type(e).__name__}")
            logger.error(f"RDP_CONFIG:   - Mensagem: {e}")
            return False
