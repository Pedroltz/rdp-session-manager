#!/usr/bin/env python3
"""
Log and audit system
"""

import logging
import logging.handlers
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class AuditLogger:
    """Specific logger for auditing administrative actions"""

    def __init__(self, log_dir: str = "/var/log/rdp-session-manager"):
        self.log_dir = Path(log_dir)
        self.audit_file = self.log_dir / "audit.log"
        self.json_audit_file = self.log_dir / "audit.json"

        # Create log directory if it does not exist
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback to user directory
            self.log_dir = Path.home() / ".local" / "share" / "rdp-session-manager" / "logs"
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.audit_file = self.log_dir / "audit.log"
            self.json_audit_file = self.log_dir / "audit.json"

    def log_event(self, event_type: str, action: str, username: str = "",
                 target_user: str = "", details: Dict = None, success: bool = True):
        """
        Records audit event

        Args:
            event_type: Event type (user_create, user_delete, etc.)
            action: Description of the action
            username: User who performed the action
            target_user: Target user of the action
            details: Additional details
            success: If the action was successful
        """
        timestamp = datetime.now()

        # Log structured in JSON
        audit_entry = {
            'timestamp': timestamp.isoformat(),
            'event_type': event_type,
            'action': action,
            'user': username,
            'target_user': target_user,
            'success': success,
            'details': details or {}
        }

        try:
            # Escrever log JSON
            with open(self.json_audit_file, 'a') as f:
                json.dump(audit_entry, f)
                f.write('\n')

            # Escrever log texto
            log_line = f"[{timestamp}] {event_type.upper()}: {action}"
            if target_user:
                log_line += f" - Target: {target_user}"
            log_line += f" - Success: {success}\n"

            with open(self.audit_file, 'a') as f:
                f.write(log_line)

        except Exception as e:
            logging.error(f"Error writing audit log: {e}")

    def get_recent_events(self, limit: int = 100) -> list:
        """Returns recent audit events"""
        events = []

        try:
            with open(self.json_audit_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

            # Return the most recent
            return events[-limit:]

        except FileNotFoundError:
            return []
        except Exception as e:
            logging.error(f"Error reading audit events: {e}")
            return []

    def get_user_events(self, username: str, limit: int = 50) -> list:
        """Returns events related to a specific user"""
        all_events = self.get_recent_events(limit=1000)

        user_events = [
            e for e in all_events
            if e.get('user') == username or e.get('target_user') == username
        ]

        return user_events[-limit:]


def setup_logger(name: str = 'rdp-session-manager',
                log_level: int = logging.INFO,
                log_dir: Optional[str] = None) -> logging.Logger:
    """
    Configure the logging system

    Args:
        name: Name of the logger
        log_level: Log level
        log_dir: Directory for log files

    Returns:
        Logger configurado
    """
    # Configure ROOT logger to capture ALL logs from ALL modules
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Avoid duplication of handlers
    if root_logger.handlers:
        return logging.getLogger(name)

    # Formata logs
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler
    if log_dir:
        log_path = Path(log_dir)
    else:
        log_path = Path.home() / ".local" / "share" / "rdp-session-manager" / "logs"

    try:
        log_path.mkdir(parents=True, exist_ok=True)
        log_file = log_path / "rdp-session-manager.log"

        # Rotating file handler (10MB max, 5 backups)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    except Exception as e:
        root_logger.warning(f"Unable to create log file: {e}")

    # Return the specific logger of this module
    return logging.getLogger(name)


def get_logger(name: str = 'rdp-session-manager') -> logging.Logger:
    """Returns existing logger or creates a new one"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        return setup_logger(name)

    return logger
