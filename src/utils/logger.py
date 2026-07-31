#!/usr/bin/env python3
"""
Sistema de logs e auditoria
"""

import logging
import logging.handlers
import os
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional


class AuditLogger:
    """Logger específico para auditoria de ações administrativas"""

    def __init__(self, log_dir: str = "/var/log/rdp-session-manager"):
        self.log_dir = Path(log_dir)
        self.audit_file = self.log_dir / "audit.log"
        self.json_audit_file = self.log_dir / "audit.json"

        # Criar diretório de logs se não existir
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            # Fallback para diretório do usuário
            self.log_dir = Path.home() / ".local" / "share" / "rdp-session-manager" / "logs"
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.audit_file = self.log_dir / "audit.log"
            self.json_audit_file = self.log_dir / "audit.json"

    def log_event(self, event_type: str, action: str, username: str = "",
                 target_user: str = "", details: Dict = None, success: bool = True):
        """
        Registra evento de auditoria

        Args:
            event_type: Tipo do evento (user_create, user_delete, etc)
            action: Descrição da ação
            username: Usuário que executou a ação
            target_user: Usuário alvo da ação
            details: Detalhes adicionais
            success: Se a ação foi bem sucedida
        """
        timestamp = datetime.now()

        # Log estruturado em JSON
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
        """Retorna eventos recentes de auditoria"""
        events = []

        try:
            with open(self.json_audit_file, 'r') as f:
                for line in f:
                    try:
                        event = json.loads(line)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

            # Retornar os mais recentes
            return events[-limit:]

        except FileNotFoundError:
            return []
        except Exception as e:
            logging.error(f"Error reading audit events: {e}")
            return []

    def get_user_events(self, username: str, limit: int = 50) -> list:
        """Retorna eventos relacionados a um usuário específico"""
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
    Configura o sistema de logging

    Args:
        name: Nome do logger
        log_level: Nível de log
        log_dir: Diretório para arquivos de log

    Returns:
        Logger configurado
    """
    # Configurar o ROOT logger para capturar TODOS os logs de TODOS os módulos
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Evitar duplicação de handlers
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
        root_logger.warning(f"Could not create log file: {e}")

    # Retornar o logger específico deste módulo
    return logging.getLogger(name)


def get_logger(name: str = 'rdp-session-manager') -> logging.Logger:
    """Retorna logger existente ou cria um novo"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        return setup_logger(name)

    return logger
