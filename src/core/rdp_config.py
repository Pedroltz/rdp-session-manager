#!/usr/bin/env python3
"""
Módulo de configuração RDP
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import Dict

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
        logger.info("RDP_CONFIG: Método create_user_session() CHAMADO")
        logger.info(f"  - Username: {username}")
        logger.info(f"  - UID: {uid}")
        logger.info(f"  - Desktop ENV: {desktop_env}")
        logger.info(f"  - RDP Port: {rdp_port}")
        logger.info("=" * 70)

        try:
            # Configurar xrdp
            logger.info("RDP_CONFIG: Gerando configuração de sessão xrdp...")
            session_config = self._generate_xrdp_session_config(
                username, desktop_env, rdp_port
            )
            logger.info(f"RDP_CONFIG: Comando de start: {session_config['start_command']}")

            # Determinar home directory
            home_dir = f"/opt/rdp-users/{username}"
            logger.info(f"RDP_CONFIG: Home directory: {home_dir}")

            # Criar script .xsession
            de_command = session_config['start_command']
            logger.info(f"RDP_CONFIG: Criando arquivo .xsession com comando: {de_command}")

            success = self._create_session_startup_script(username, de_command, home_dir)

            if not success:
                logger.error(f"RDP_CONFIG: ERRO - Falha ao criar script .xsession para {username}")
                return False

            logger.info("=" * 70)
            logger.info(f"RDP_CONFIG: SUCESSO - Configuração RDP criada para {username}")
            logger.info(f"  - Porta: {rdp_port}")
            logger.info(f"  - Arquivo .xsession criado em: {home_dir}/.xsession")
            logger.info("=" * 70)
            return True

        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"RDP_CONFIG: ERRO ao criar configuração RDP para {username}")
            logger.error(f"  - Exceção: {type(e).__name__}")
            logger.error(f"  - Mensagem: {e}")
            logger.error("=" * 70)
            return False

    def _generate_xrdp_session_config(self, username: str, desktop_env: str,
                                     rdp_port: int) -> Dict:
        """Gera configuração de sessão xrdp"""

        # Determinar comando de inicialização do DE
        de_commands = {
            'gnome': 'gnome-session',
            'xfce': 'startxfce4',
            'xfce4': 'startxfce4',
            'kde': 'startplasma-x11',
            'plasma': 'startplasma-x11',
            'mate': 'mate-session',
            'cinnamon': 'cinnamon-session',
            'lxde': 'startlxde',
            'lxqt': 'startlxqt',
        }

        de_command = de_commands.get(desktop_env.lower(), 'startxfce4')

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
        logger.info(f"RDP_CONFIG: Verificando script .xsession para {username}...")
        logger.info(f"RDP_CONFIG:   - Home: {home_dir}")
        logger.info(f"RDP_CONFIG:   - Comando DE: {de_command}")

        try:
            # O arquivo .xsession já deve ter sido criado pelo user_manager durante create_user
            # Apenas verificar se existe
            xsession_path = Path(home_dir) / ".xsession"

            if xsession_path.exists():
                logger.info(f"RDP_CONFIG: ✓ Script .xsession já existe")
                logger.info(f"RDP_CONFIG:   - Arquivo: {xsession_path}")
                return True
            else:
                logger.warning(f"RDP_CONFIG: ⚠ Script .xsession não encontrado")
                logger.warning(f"RDP_CONFIG:   - Isso pode indicar um problema durante a criação do usuário")
                logger.warning(f"RDP_CONFIG:   - O arquivo deveria ter sido criado automaticamente")
                return False

        except Exception as e:
            logger.error(f"RDP_CONFIG: EXCEÇÃO ao verificar script de inicialização")
            logger.error(f"RDP_CONFIG:   - Tipo: {type(e).__name__}")
            logger.error(f"RDP_CONFIG:   - Mensagem: {e}")
            return False

