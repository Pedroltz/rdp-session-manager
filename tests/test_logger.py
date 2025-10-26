#!/usr/bin/env python3
"""
Tests for Logger module
"""

import unittest
import sys
import json
import tempfile
import shutil
import logging
from pathlib import Path
from unittest.mock import patch, Mock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils.logger import AuditLogger, setup_logger, get_logger


class TestAuditLogger(unittest.TestCase):
    """Test AuditLogger class"""

    def setUp(self):
        """Setup test fixtures"""
        # Criar diretório temporário para logs
        self.test_dir = Path(tempfile.mkdtemp())
        self.audit_logger = AuditLogger(str(self.test_dir))

    def tearDown(self):
        """Cleanup test fixtures"""
        # Remover diretório temporário
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_audit_logger_initialization(self):
        """Test AuditLogger initialization"""
        self.assertIsNotNone(self.audit_logger)
        self.assertTrue(self.audit_logger.log_dir.exists())
        self.assertEqual(self.audit_logger.log_dir, self.test_dir)

    @patch('pathlib.Path.home')
    def test_audit_logger_fallback_to_home(self, mock_home):
        """Test AuditLogger fallback to home directory on permission error"""
        mock_home.return_value = self.test_dir

        # Criar um diretório que vai dar PermissionError
        restricted_dir = Path("/var/log/restricted_test_dir")

        # Tentar criar logger em diretório restrito (vai falhar e usar fallback)
        # Não vamos mockar mkdir, vamos apenas deixar que o código real falhe naturalmente
        # e faça fallback para o home directory
        logger = AuditLogger(str(restricted_dir))

        # Deve ter feito fallback para diretório home
        expected_dir = self.test_dir / ".local" / "share" / "rdp-session-manager" / "logs"
        self.assertEqual(str(logger.log_dir), str(expected_dir))

    def test_log_event_creates_files(self):
        """Test that log_event creates log files"""
        self.audit_logger.log_event(
            event_type='test_event',
            action='Test action',
            username='testuser',
            target_user='targetuser',
            success=True
        )

        # Verificar que arquivos foram criados
        self.assertTrue(self.audit_logger.audit_file.exists())
        self.assertTrue(self.audit_logger.json_audit_file.exists())

    def test_log_event_json_format(self):
        """Test that log_event writes correct JSON format"""
        self.audit_logger.log_event(
            event_type='user_create',
            action='Created user',
            username='admin',
            target_user='newuser',
            details={'uid': 5000, 'desktop': 'xfce'},
            success=True
        )

        # Ler arquivo JSON
        with open(self.audit_logger.json_audit_file, 'r') as f:
            log_line = f.readline()
            event = json.loads(log_line)

        # Verificar campos
        self.assertEqual(event['event_type'], 'user_create')
        self.assertEqual(event['action'], 'Created user')
        self.assertEqual(event['user'], 'admin')
        self.assertEqual(event['target_user'], 'newuser')
        self.assertTrue(event['success'])
        self.assertIn('timestamp', event)
        self.assertIn('details', event)
        self.assertEqual(event['details']['uid'], 5000)

    def test_log_event_text_format(self):
        """Test that log_event writes correct text format"""
        self.audit_logger.log_event(
            event_type='user_delete',
            action='Deleted user',
            target_user='olduser',
            success=True
        )

        # Ler arquivo texto
        with open(self.audit_logger.audit_file, 'r') as f:
            log_line = f.readline()

        # Verificar conteúdo
        self.assertIn('USER_DELETE', log_line)
        self.assertIn('Deleted user', log_line)
        self.assertIn('olduser', log_line)
        self.assertIn('Success: True', log_line)

    def test_log_event_multiple_events(self):
        """Test logging multiple events"""
        # Registrar vários eventos
        for i in range(5):
            self.audit_logger.log_event(
                event_type=f'event_{i}',
                action=f'Action {i}',
                success=True
            )

        # Verificar que todos foram registrados
        with open(self.audit_logger.json_audit_file, 'r') as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 5)

    def test_get_recent_events(self):
        """Test get_recent_events method"""
        # Registrar alguns eventos
        for i in range(10):
            self.audit_logger.log_event(
                event_type=f'event_{i}',
                action=f'Action {i}',
                success=True
            )

        # Obter eventos recentes
        events = self.audit_logger.get_recent_events(limit=5)

        self.assertEqual(len(events), 5)
        # Deve retornar os mais recentes (5-9)
        self.assertEqual(events[0]['event_type'], 'event_5')
        self.assertEqual(events[4]['event_type'], 'event_9')

    def test_get_recent_events_empty(self):
        """Test get_recent_events with no events"""
        events = self.audit_logger.get_recent_events()

        self.assertEqual(len(events), 0)

    def test_get_user_events(self):
        """Test get_user_events method"""
        # Registrar eventos de diferentes usuários
        self.audit_logger.log_event('event1', 'Action 1', username='user1', success=True)
        self.audit_logger.log_event('event2', 'Action 2', username='user2', success=True)
        self.audit_logger.log_event('event3', 'Action 3', target_user='user1', success=True)
        self.audit_logger.log_event('event4', 'Action 4', username='user1', success=True)

        # Obter eventos do user1
        events = self.audit_logger.get_user_events('user1')

        # Deve retornar 3 eventos (onde user1 é user ou target_user)
        self.assertEqual(len(events), 3)

    def test_get_user_events_not_found(self):
        """Test get_user_events with non-existent user"""
        self.audit_logger.log_event('event1', 'Action 1', username='user1', success=True)

        # Buscar usuário inexistente
        events = self.audit_logger.get_user_events('nonexistent')

        self.assertEqual(len(events), 0)

    def test_log_event_with_no_details(self):
        """Test log_event without details"""
        self.audit_logger.log_event(
            event_type='simple_event',
            action='Simple action',
            success=True
        )

        # Ler evento
        with open(self.audit_logger.json_audit_file, 'r') as f:
            event = json.loads(f.readline())

        # details deve ser um dicionário vazio
        self.assertEqual(event['details'], {})

    def test_log_event_failure(self):
        """Test logging failed events"""
        self.audit_logger.log_event(
            event_type='failed_action',
            action='Failed to do something',
            success=False
        )

        # Verificar que foi registrado como falha
        with open(self.audit_logger.json_audit_file, 'r') as f:
            event = json.loads(f.readline())

        self.assertFalse(event['success'])


class TestLoggerSetup(unittest.TestCase):
    """Test logger setup functions"""

    def setUp(self):
        """Setup test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        # Limpar handlers do root logger
        logging.getLogger().handlers = []

    def tearDown(self):
        """Cleanup test fixtures"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        # Limpar handlers novamente
        logging.getLogger().handlers = []

    def test_setup_logger_creates_logger(self):
        """Test that setup_logger creates a logger"""
        logger = setup_logger('test-logger', log_dir=str(self.test_dir))

        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'test-logger')

    def test_setup_logger_creates_log_file(self):
        """Test that setup_logger creates log file"""
        logger = setup_logger('test-logger', log_dir=str(self.test_dir))

        # Escrever log
        logger.info("Test message")

        # Verificar que arquivo foi criado
        log_file = self.test_dir / "rdp-session-manager.log"
        self.assertTrue(log_file.exists())

    def test_setup_logger_default_level(self):
        """Test setup_logger default log level"""
        logger = setup_logger('test-logger', log_dir=str(self.test_dir))

        # Nível padrão deve ser INFO
        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.INFO)

    def test_setup_logger_custom_level(self):
        """Test setup_logger with custom log level"""
        logger = setup_logger('test-logger', log_level=logging.DEBUG, log_dir=str(self.test_dir))

        root_logger = logging.getLogger()
        self.assertEqual(root_logger.level, logging.DEBUG)

    def test_setup_logger_no_duplicate_handlers(self):
        """Test that setup_logger doesn't create duplicate handlers"""
        logger1 = setup_logger('test-logger', log_dir=str(self.test_dir))
        initial_handler_count = len(logging.getLogger().handlers)

        logger2 = setup_logger('test-logger', log_dir=str(self.test_dir))
        final_handler_count = len(logging.getLogger().handlers)

        # Número de handlers não deve aumentar
        self.assertEqual(initial_handler_count, final_handler_count)

    @patch('pathlib.Path.home')
    def test_setup_logger_default_location(self, mock_home):
        """Test setup_logger with default log directory"""
        mock_home.return_value = self.test_dir

        logger = setup_logger('test-logger')

        # Deve criar no diretório padrão
        expected_log_path = self.test_dir / ".local" / "share" / "rdp-session-manager" / "logs"
        self.assertTrue(expected_log_path.exists())

    def test_get_logger_creates_if_not_exists(self):
        """Test get_logger creates logger if doesn't exist"""
        logger = get_logger('new-logger')

        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, 'new-logger')

    def test_get_logger_returns_existing(self):
        """Test get_logger returns existing logger"""
        logger1 = setup_logger('existing-logger', log_dir=str(self.test_dir))
        logger2 = get_logger('existing-logger')

        # Deve retornar o mesmo logger
        self.assertEqual(logger1.name, logger2.name)

    def test_logger_console_handler(self):
        """Test that logger has console handler"""
        logger = setup_logger('test-logger', log_dir=str(self.test_dir))

        root_logger = logging.getLogger()
        # Deve ter pelo menos um StreamHandler (console)
        console_handlers = [h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)]
        self.assertGreater(len(console_handlers), 0)

    def test_logger_file_handler(self):
        """Test that logger has file handler"""
        logger = setup_logger('test-logger', log_dir=str(self.test_dir))

        root_logger = logging.getLogger()
        # Deve ter pelo menos um RotatingFileHandler
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
        self.assertGreater(len(file_handlers), 0)

    def test_logger_rotating_file_handler_config(self):
        """Test rotating file handler configuration"""
        logger = setup_logger('test-logger', log_dir=str(self.test_dir))

        root_logger = logging.getLogger()
        file_handlers = [h for h in root_logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]

        if file_handlers:
            handler = file_handlers[0]
            # Verificar configurações
            self.assertEqual(handler.maxBytes, 10*1024*1024)  # 10MB
            self.assertEqual(handler.backupCount, 5)


if __name__ == '__main__':
    unittest.main()
