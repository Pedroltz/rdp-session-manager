#!/usr/bin/env python3
"""
Tests for SessionMonitor module
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from core.session_monitor import SessionMonitor, SessionInfo


class TestSessionInfo(unittest.TestCase):
    """Test SessionInfo class"""

    def test_session_info_creation(self):
        """Test SessionInfo initialization"""
        session = SessionInfo(
            username='testuser',
            session_id='12345',
            ip_address='192.168.1.100',
            port=3389,
            connected=True
        )

        self.assertEqual(session.username, 'testuser')
        self.assertEqual(session.session_id, '12345')
        self.assertEqual(session.ip_address, '192.168.1.100')
        self.assertEqual(session.port, 3389)
        self.assertTrue(session.connected)

    def test_session_info_to_dict(self):
        """Test SessionInfo to_dict method"""
        start_time = datetime.now()
        session = SessionInfo(
            username='testuser',
            session_id='12345',
            ip_address='192.168.1.100',
            port=3389,
            connected=True,
            start_time=start_time
        )

        session_dict = session.to_dict()

        self.assertEqual(session_dict['username'], 'testuser')
        self.assertEqual(session_dict['session_id'], '12345')
        self.assertEqual(session_dict['ip_address'], '192.168.1.100')
        self.assertEqual(session_dict['port'], 3389)
        self.assertTrue(session_dict['connected'])
        self.assertEqual(session_dict['start_time'], start_time.isoformat())
        self.assertIn('duration', session_dict)

    def test_session_info_get_duration(self):
        """Test SessionInfo get_duration method"""
        # Sessão iniciada há 60 segundos
        start_time = datetime.now() - timedelta(seconds=60)
        session = SessionInfo(
            username='testuser',
            start_time=start_time
        )

        duration = session.get_duration()

        # Duração deve ser aproximadamente 60 segundos (com margem de 2 segundos)
        self.assertGreaterEqual(duration, 58)
        self.assertLessEqual(duration, 62)

    def test_session_info_default_start_time(self):
        """Test SessionInfo with default start_time"""
        session = SessionInfo(username='testuser')

        # start_time deve ser definido automaticamente
        self.assertIsNotNone(session.start_time)
        self.assertIsInstance(session.start_time, datetime)

        # Duração deve ser próxima de 0
        duration = session.get_duration()
        self.assertLessEqual(duration, 2)


class TestSessionMonitor(unittest.TestCase):
    """Test SessionMonitor class"""

    def setUp(self):
        """Setup test fixtures"""
        self.monitor = SessionMonitor()

    def test_session_monitor_initialization(self):
        """Test SessionMonitor initialization"""
        self.assertIsNotNone(self.monitor)
        self.assertIsInstance(self.monitor.sessions, dict)

    @patch('subprocess.run')
    @patch('psutil.process_iter')
    def test_get_active_sessions_no_processes(self, mock_process_iter, mock_subprocess):
        """Test get_active_sessions with no xrdp processes"""
        # Simular processos sem xrdp
        mock_proc = Mock()
        mock_proc.info = {'pid': 1234, 'name': 'bash', 'username': 'user'}
        mock_process_iter.return_value = [mock_proc]

        # Simular loginctl sem sessões
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ''
        mock_subprocess.return_value = mock_result

        sessions = self.monitor.get_active_sessions()

        self.assertEqual(len(sessions), 0)

    @patch('subprocess.run')
    @patch('psutil.process_iter')
    def test_get_active_sessions_with_xrdp(self, mock_process_iter, mock_subprocess):
        """Test get_active_sessions with xrdp processes"""
        # Criar mock de processo xrdp
        mock_proc = Mock()
        mock_proc.info = {'pid': 5678, 'name': 'xrdp-sesman', 'username': 'testuser'}

        # Criar mock de conexão
        mock_conn = Mock()
        mock_conn.status = 'ESTABLISHED'
        mock_conn.raddr = Mock(ip='192.168.1.100')
        mock_conn.laddr = Mock(port=3389)

        mock_proc.connections.return_value = [mock_conn]
        mock_process_iter.return_value = [mock_proc]

        # Simular loginctl sem sessões (para não duplicar)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = ''
        mock_subprocess.return_value = mock_result

        sessions = self.monitor.get_active_sessions()

        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0].username, 'testuser')
        self.assertEqual(sessions[0].ip_address, '192.168.1.100')
        self.assertEqual(sessions[0].port, 3389)

    def test_get_user_session_not_found(self):
        """Test get_user_session when user has no session"""
        with patch.object(self.monitor, 'get_active_sessions', return_value=[]):
            session = self.monitor.get_user_session('nonexistent')
            self.assertIsNone(session)

    def test_get_user_session_found(self):
        """Test get_user_session when user has session"""
        mock_session = SessionInfo(username='testuser', connected=True)

        with patch.object(self.monitor, 'get_active_sessions', return_value=[mock_session]):
            session = self.monitor.get_user_session('testuser')
            self.assertIsNotNone(session)
            self.assertEqual(session.username, 'testuser')

    def test_is_user_connected(self):
        """Test is_user_connected method"""
        mock_session = SessionInfo(username='testuser', connected=True)

        with patch.object(self.monitor, 'get_user_session', return_value=mock_session):
            self.assertTrue(self.monitor.is_user_connected('testuser'))

        with patch.object(self.monitor, 'get_user_session', return_value=None):
            self.assertFalse(self.monitor.is_user_connected('testuser'))

    def test_get_session_count(self):
        """Test get_session_count method"""
        mock_sessions = [
            SessionInfo(username='user1'),
            SessionInfo(username='user2'),
            SessionInfo(username='user3')
        ]

        with patch.object(self.monitor, 'get_active_sessions', return_value=mock_sessions):
            count = self.monitor.get_session_count()
            self.assertEqual(count, 3)

    @patch('socket.socket')
    def test_get_ip_address(self, mock_socket):
        """Test get_ip_address method"""
        # Criar mock do socket
        mock_sock = MagicMock()
        mock_sock.getsockname.return_value = ('192.168.1.50', 0)
        mock_socket.return_value = mock_sock

        ip = self.monitor.get_ip_address()

        self.assertEqual(ip, '192.168.1.50')

    @patch('socket.socket')
    def test_get_ip_address_fallback(self, mock_socket):
        """Test get_ip_address fallback to localhost"""
        # Simular erro no socket
        mock_socket.side_effect = Exception("Network error")

        with patch('socket.gethostname', return_value='testhost'):
            with patch('socket.gethostbyname', return_value='192.168.1.99'):
                ip = self.monitor.get_ip_address()
                self.assertEqual(ip, '192.168.1.99')

    @patch('psutil.net_if_addrs')
    def test_get_all_network_ips(self, mock_net_if_addrs):
        """Test get_all_network_ips method"""
        # Criar mock de interfaces de rede
        mock_snic = Mock()
        mock_snic.family = 2  # AF_INET
        mock_snic.address = '192.168.1.100'

        mock_net_if_addrs.return_value = {
            'eth0': [mock_snic]
        }

        ips = self.monitor.get_all_network_ips()

        self.assertIn('192.168.1.100', ips)
        self.assertNotIn('127.0.0.1', ips)

    @patch('psutil.process_iter')
    def test_kill_user_session(self, mock_process_iter):
        """Test kill_user_session method"""
        # Criar mock de processo
        mock_proc = Mock()
        mock_proc.info = {'pid': 9999, 'name': 'bash', 'username': 'testuser'}
        mock_process_iter.return_value = [mock_proc]

        result = self.monitor.kill_user_session('testuser')

        self.assertTrue(result)
        mock_proc.kill.assert_called_once()

    @patch('psutil.cpu_percent')
    @patch('psutil.virtual_memory')
    @patch('psutil.disk_usage')
    def test_get_system_stats(self, mock_disk, mock_memory, mock_cpu):
        """Test get_system_stats method"""
        # Configurar mocks
        mock_cpu.return_value = 50.0

        mock_mem = Mock()
        mock_mem.percent = 75.0
        mock_mem.used = 8 * 1024**3  # 8GB
        mock_mem.total = 16 * 1024**3  # 16GB
        mock_memory.return_value = mock_mem

        mock_dsk = Mock()
        mock_dsk.percent = 60.0
        mock_dsk.used = 100 * 1024**3  # 100GB
        mock_dsk.total = 500 * 1024**3  # 500GB
        mock_disk.return_value = mock_dsk

        with patch.object(self.monitor, 'get_session_count', return_value=3):
            stats = self.monitor.get_system_stats()

            self.assertEqual(stats['cpu_percent'], 50.0)
            self.assertEqual(stats['memory_percent'], 75.0)
            self.assertAlmostEqual(stats['memory_used_gb'], 8.0, places=1)
            self.assertAlmostEqual(stats['memory_total_gb'], 16.0, places=1)
            self.assertEqual(stats['disk_percent'], 60.0)
            self.assertEqual(stats['active_sessions'], 3)

    @patch('socket.socket')
    def test_check_port_status_open(self, mock_socket):
        """Test check_port_status with open port"""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 0  # Porta aberta
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = self.monitor.check_port_status(3389)

        self.assertTrue(result)

    @patch('socket.socket')
    def test_check_port_status_closed(self, mock_socket):
        """Test check_port_status with closed port"""
        mock_sock = MagicMock()
        mock_sock.connect_ex.return_value = 1  # Porta fechada
        mock_socket.return_value.__enter__.return_value = mock_sock

        result = self.monitor.check_port_status(9999)

        self.assertFalse(result)

    def test_get_connection_history(self):
        """Test get_connection_history method"""
        # Por enquanto retorna lista vazia (não implementado)
        history = self.monitor.get_connection_history('testuser')

        self.assertIsInstance(history, list)
        self.assertEqual(len(history), 0)


if __name__ == '__main__':
    unittest.main()
