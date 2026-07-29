#!/usr/bin/env python3
"""
Application configuration module
"""

import logging
import configparser
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class AppConfig:
    """Application Settings Manager"""

    def __init__(self):
        # Configuration directory
        self.config_dir = Path.home() / '.config' / 'rdp-session-manager'
        self.config_file = self.config_dir / 'config.ini'

        # Default values
        self.defaults = {
            'rdp': {
                'default_port': '3389'
            }
        }

        # Create directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Load or create configuration
        self.config = configparser.ConfigParser()
        self._load_or_create()

    def _load_or_create(self):
        """Loads existing configuration or creates with default values"""
        if self.config_file.exists():
            try:
                self.config.read(self.config_file)
                logger.info(f"Configuration loaded from {self.config_file}")

                # Ensure sections exist
                for section, options in self.defaults.items():
                    if not self.config.has_section(section):
                        self.config.add_section(section)
                    for key, value in options.items():
                        if not self.config.has_option(section, key):
                            self.config.set(section, key, value)

                # Save if changes are made
                self._save()

            except Exception as e:
                logger.error(f"Error loading configuration: {e}")
                self._create_default()
        else:
            logger.info("Configuration file does not exist, creating with default values")
            self._create_default()

    def _create_default(self):
        """Create configuration file with default values"""
        for section, options in self.defaults.items():
            self.config.add_section(section)
            for key, value in options.items():
                self.config.set(section, key, value)

        self._save()
        logger.info(f"Default configuration created in {self.config_file}")

    def _save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                self.config.write(f)
            logger.debug(f"Configuration saved in {self.config_file}")
        except Exception as e:
            logger.error(f"Error saving configuration: {e}")

    def get_default_rdp_port(self) -> int:
        """Gets the default RDP port"""
        try:
            port_str = self.config.get('rdp', 'default_port', fallback='3389')
            port = int(port_str)

            # Validate port
            if port < 1 or port > 65535:
                logger.warning(f"Invalid port: {port}, using 3389")
                return 3389

            return port
        except Exception as e:
            logger.error(f"Error getting default port: {e}")
            return 3389

    def set_default_rdp_port(self, port: int) -> bool:
        """Set the default RDP port"""
        try:
            # Validate port
            if port < 1 or port > 65535:
                logger.error(f"Invalid port: {port}")
                return False

            # Ensure that section exists
            if not self.config.has_section('rdp'):
                self.config.add_section('rdp')

            # Set value
            self.config.set('rdp', 'default_port', str(port))

            # Save
            self._save()

            logger.info(f"Default RDP port changed to: {port}")
            return True

        except Exception as e:
            logger.error(f"Error setting default port: {e}")
            return False

    def get(self, section: str, key: str, fallback: Optional[str] = None) -> Optional[str]:
        """Gets a generic configuration value"""
        try:
            return self.config.get(section, key, fallback=fallback)
        except Exception as e:
            logger.error(f"Error getting configuration [{section}].{key}: {e}")
            return fallback

    def set(self, section: str, key: str, value: str) -> bool:
        """Defines a generic configuration value"""
        try:
            if not self.config.has_section(section):
                self.config.add_section(section)

            self.config.set(section, key, value)
            self._save()
            return True

        except Exception as e:
            logger.error(f"Error setting configuration [{section}].{key}: {e}")
            return False
