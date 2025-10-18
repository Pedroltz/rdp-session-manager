#!/usr/bin/env python3
"""
Sistema de backup de configurações
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """Gerenciador de backup de configurações"""

    def __init__(self, backup_dir: str = None):
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = Path.home() / ".local" / "share" / "rdp-session-manager" / "backups"

        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, user_data: Dict) -> Optional[Path]:
        """
        Cria backup das configurações de um usuário

        Args:
            user_data: Dados do usuário para backup

        Returns:
            Path do arquivo de backup ou None se falhar
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            username = user_data.get('username', 'unknown')

            backup_file = self.backup_dir / f"backup_{username}_{timestamp}.json"

            with open(backup_file, 'w') as f:
                json.dump({
                    'timestamp': timestamp,
                    'version': '1.0',
                    'user_data': user_data
                }, f, indent=2)

            logger.info(f"Backup created: {backup_file}")
            return backup_file

        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None

    def restore_backup(self, backup_file: Path) -> Optional[Dict]:
        """
        Restaura configuração de um arquivo de backup

        Args:
            backup_file: Path do arquivo de backup

        Returns:
            Dicionário com dados do usuário ou None se falhar
        """
        try:
            with open(backup_file, 'r') as f:
                backup_data = json.load(f)

            logger.info(f"Backup restored from: {backup_file}")
            return backup_data.get('user_data')

        except Exception as e:
            logger.error(f"Error restoring backup: {e}")
            return None

    def list_backups(self, username: str = None) -> list:
        """
        Lista backups disponíveis

        Args:
            username: Filtrar por usuário específico (opcional)

        Returns:
            Lista de arquivos de backup
        """
        try:
            pattern = f"backup_{username}_*.json" if username else "backup_*.json"
            backups = sorted(self.backup_dir.glob(pattern), reverse=True)

            return backups

        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    def delete_backup(self, backup_file: Path) -> bool:
        """Remove um arquivo de backup"""
        try:
            backup_file.unlink()
            logger.info(f"Backup deleted: {backup_file}")
            return True

        except Exception as e:
            logger.error(f"Error deleting backup: {e}")
            return False

    def cleanup_old_backups(self, days: int = 30, username: str = None) -> int:
        """
        Remove backups antigos

        Args:
            days: Remover backups mais antigos que N dias
            username: Filtrar por usuário específico (opcional)

        Returns:
            Número de backups removidos
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=days)
            backups = self.list_backups(username)

            removed = 0

            for backup in backups:
                # Extrair timestamp do nome do arquivo
                parts = backup.stem.split('_')

                if len(parts) >= 3:
                    date_str = parts[-2]
                    time_str = parts[-1]

                    try:
                        backup_date = datetime.strptime(f"{date_str}_{time_str}", "%Y%m%d_%H%M%S")

                        if backup_date < cutoff_date:
                            if self.delete_backup(backup):
                                removed += 1

                    except ValueError:
                        continue

            logger.info(f"Cleaned up {removed} old backups")
            return removed

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return 0

    def export_all_configs(self, export_file: Path) -> bool:
        """
        Exporta todas as configurações para um arquivo

        Args:
            export_file: Path do arquivo de exportação

        Returns:
            True se sucesso
        """
        try:
            # Coletar todos os backups
            all_backups = []

            for backup in self.list_backups():
                data = self.restore_backup(backup)

                if data:
                    all_backups.append(data)

            # Exportar
            with open(export_file, 'w') as f:
                json.dump({
                    'export_date': datetime.now().isoformat(),
                    'version': '1.0',
                    'users': all_backups
                }, f, indent=2)

            logger.info(f"All configs exported to: {export_file}")
            return True

        except Exception as e:
            logger.error(f"Error exporting configs: {e}")
            return False

    def import_configs(self, import_file: Path) -> bool:
        """
        Importa configurações de um arquivo

        Args:
            import_file: Path do arquivo de importação

        Returns:
            True se sucesso
        """
        try:
            with open(import_file, 'r') as f:
                import_data = json.load(f)

            users = import_data.get('users', [])

            for user_data in users:
                self.create_backup(user_data)

            logger.info(f"Configs imported from: {import_file}")
            return True

        except Exception as e:
            logger.error(f"Error importing configs: {e}")
            return False
