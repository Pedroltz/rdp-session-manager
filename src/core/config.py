#!/usr/bin/env python3
"""
Módulo de configuração da aplicação
"""

import logging
import configparser
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AppConfig:
    """Gerenciador de configurações da aplicação"""

    def __init__(self):
        # Diretório de configuração
        self.config_dir = Path.home() / '.config' / 'rdp-session-manager'
        self.config_file = self.config_dir / 'config.ini'

        # Valores padrão
        self.defaults = {
            'rdp': {
                'default_port': '3389'
            }
        }

        # Criar diretório se não existir
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Carregar ou criar configuração
        self.config = configparser.ConfigParser()
        self._load_or_create()

    def _load_or_create(self):
        """Carrega configuração existente ou cria com valores padrão"""
        if self.config_file.exists():
            try:
                self.config.read(self.config_file)
                logger.info(f"Configuração carregada de {self.config_file}")

                # Garantir que seções existam
                for section, options in self.defaults.items():
                    if not self.config.has_section(section):
                        self.config.add_section(section)
                    for key, value in options.items():
                        if not self.config.has_option(section, key):
                            self.config.set(section, key, value)

                # Salvar se houver mudanças
                self._save()

            except Exception as e:
                logger.error(f"Erro ao carregar configuração: {e}")
                self._create_default()
        else:
            logger.info("Arquivo de configuração não existe, criando com valores padrão")
            self._create_default()

    def _create_default(self):
        """Cria arquivo de configuração com valores padrão"""
        for section, options in self.defaults.items():
            self.config.add_section(section)
            for key, value in options.items():
                self.config.set(section, key, value)

        self._save()
        logger.info(f"Configuração padrão criada em {self.config_file}")

    def _save(self):
        """Salva configuração no arquivo"""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            logger.debug(f"Configuração salva em {self.config_file}")
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")

    def get_default_rdp_port(self) -> int:
        """Obtém a porta RDP padrão"""
        try:
            port_str = self.config.get('rdp', 'default_port', fallback='3389')
            port = int(port_str)

            # Validar porta
            if port < 1 or port > 65535:
                logger.warning(f"Porta inválida: {port}, usando 3389")
                return 3389

            return port
        except Exception as e:
            logger.error(f"Erro ao obter porta padrão: {e}")
            return 3389

    def set_default_rdp_port(self, port: int) -> bool:
        """Define a porta RDP padrão"""
        try:
            # Validar porta
            if port < 1 or port > 65535:
                logger.error(f"Porta inválida: {port}")
                return False

            # Garantir que seção existe
            if not self.config.has_section('rdp'):
                self.config.add_section('rdp')

            # Definir valor
            self.config.set('rdp', 'default_port', str(port))

            # Salvar
            self._save()

            logger.info(f"Porta RDP padrão alterada para: {port}")
            return True

        except Exception as e:
            logger.error(f"Erro ao definir porta padrão: {e}")
            return False

    def get(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """Obtém um valor de configuração genérico"""
        try:
            return self.config.get(section, key, fallback=fallback)
        except Exception as e:
            logger.error(f"Erro ao obter configuração [{section}].{key}: {e}")
            return fallback

    def set(self, section: str, key: str, value: str) -> bool:
        """Define um valor de configuração genérico"""
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)

            self.config.set(section, key, value)
            self._save()
            return True

        except Exception as e:
            logger.error(f"Erro ao definir configuração [{section}].{key}: {e}")
            return False
