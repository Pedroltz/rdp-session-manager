#!/usr/bin/env python3
"""
Settings backup system
"""

import json
import logging
import shutil
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class BackupManager:
    """Settings Backup Manager"""

    def __init__(self, backup_dir: str = None):
        if backup_dir:
            self.backup_dir = Path(backup_dir)
        else:
            self.backup_dir = Path.home() / ".local" / "share" / "rdp-session-manager" / "backups"

        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def create_backup(self, user_data: Dict) -> Optional[Path]:
        """
        Creates a backup of a user's settings

        Args:
            user_data: User data to backup

        Returns:
            Backup file path or None if it fails
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
        Restores configuration from a backup file

        Args:
            backup_file: Path of the backup file

        Returns:
            Dictionary with user data or None if failed
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
        List available backups

        Args:
            username: Filter by specific user (optional)

        Returns:
            Backup File List
        """
        try:
            pattern = f"backup_{username}_*.json" if username else "backup_*.json"
            backups = sorted(self.backup_dir.glob(pattern), reverse=True)

            return backups

        except Exception as e:
            logger.error(f"Error listing backups: {e}")
            return []

    def delete_backup(self, backup_file: Path) -> bool:
        """Remove a backup file"""
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
            days: Remove backups older than N days
            username: Filter by specific user (optional)

        Returns:
            Number of backups removed
        """
        try:
            from datetime import timedelta

            cutoff_date = datetime.now() - timedelta(days=days)
            backups = self.list_backups(username)

            removed = 0

            for backup in backups:
                # Extract timestamp from file name
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
        Export all settings to a file

        Args:
            export_file: Path of the export file

        Returns:
            True if success
        """
        try:
            # Collect all backups
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
        Import settings from a file

        Args:
            import_file: Path of the import file

        Returns:
            True if success
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
