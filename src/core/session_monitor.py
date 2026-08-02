#!/usr/bin/env python3
"""
Módulo de monitoramento de sessões RDP
"""

import subprocess
import logging
import psutil
import socket
import time
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionInfo:
    """Informações de uma sessão RDP"""

    def __init__(self, username: str, session_id: str = "", ip_address: str = "",
                 port: int = 0, connected: bool = False, start_time: datetime = None,
                 memory_mb: float = 0.0, cpu_percent: float = 0.0,
                 process_count: int = 0):
        self.username = username
        self.session_id = session_id
        self.ip_address = ip_address
        self.port = port
        self.connected = connected
        self.start_time = start_time or datetime.now()
        self.memory_mb = memory_mb
        self.cpu_percent = cpu_percent
        self.process_count = process_count

    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            'username': self.username,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'port': self.port,
            'connected': self.connected,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'duration': self.get_duration(),
            'memory_mb': round(self.memory_mb, 2),
            'cpu_percent': round(self.cpu_percent, 2),
            'process_count': self.process_count,
        }

    def get_duration(self) -> int:
        """Retorna duração da sessão em segundos"""
        if self.start_time:
            return int((datetime.now() - self.start_time).total_seconds())
        return 0


class SessionMonitor:
    """Monitor de sessões RDP"""

    def __init__(self, cache_ttl: float = 2.0):
        self.sessions = {}
        self.cache_ttl = cache_ttl
        self._sessions_cache = None
        self._sessions_cache_at = 0.0
        self._ip_cache = None

    def get_active_sessions(self) -> List[SessionInfo]:
        """Retorna lista de sessões ativas"""
        now = time.monotonic()
        if (
            self._sessions_cache is not None
            and now - self._sessions_cache_at < self.cache_ttl
        ):
            return list(self._sessions_cache)
        sessions = []

        try:
            # Verificar conexões RDP ativas
            connections = self._get_rdp_connections()

            for conn in connections:
                previous = self.sessions.get(conn.get('username', 'unknown'))
                session = SessionInfo(
                    username=conn.get('username', 'unknown'),
                    session_id=conn.get('session_id', ''),
                    ip_address=conn.get('remote_ip', ''),
                    port=conn.get('port', 0),
                    connected=True,
                    start_time=(
                        previous.start_time
                        if previous and previous.session_id == conn.get('session_id', '')
                        else None
                    ),
                )
                sessions.append(session)
            usage = self._get_user_usage({session.username for session in sessions})
            for session in sessions:
                values = usage.get(session.username, {})
                session.memory_mb = values.get('memory_mb', 0.0)
                session.cpu_percent = values.get('cpu_percent', 0.0)
                session.process_count = values.get('process_count', 0)

        except Exception as e:
            logger.error(f"Error getting active sessions: {e}")

        self._sessions_cache = list(sessions)
        self._sessions_cache_at = now
        self.sessions = {session.username: session for session in sessions}
        return sessions

    @staticmethod
    def _get_user_usage(usernames: set) -> Dict[str, Dict]:
        usage = {
            username: {'memory_mb': 0.0, 'cpu_percent': 0.0, 'process_count': 0}
            for username in usernames
        }
        if not usernames:
            return usage
        for proc in psutil.process_iter(['username', 'memory_info', 'cpu_percent']):
            try:
                username = proc.info.get('username')
                if username not in usage:
                    continue
                memory = proc.info.get('memory_info')
                usage[username]['memory_mb'] += (
                    memory.rss / (1024 * 1024) if memory else 0.0
                )
                usage[username]['cpu_percent'] += proc.info.get('cpu_percent') or 0.0
                usage[username]['process_count'] += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return usage

    def invalidate(self):
        """Invalidate cached system state after a mutating session operation."""
        self._sessions_cache = None
        self._sessions_cache_at = 0.0

    def snapshot(self) -> Dict:
        """Return one reusable state snapshot for CLI and GUI consumers."""
        sessions = self.get_active_sessions()
        return {
            'captured_at': datetime.now().isoformat(),
            'sessions': [session.to_dict() for session in sessions],
            'active_sessions': len(sessions),
            'ip_addresses': self.get_all_network_ips(),
        }

    def _get_rdp_connections(self) -> List[Dict]:
        """Obtém conexões RDP ativas do sistema"""
        connections = []
        seen_users = set()

        try:
            # Método 1: Verificar processos xrdp-sesman de usuários específicos
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    # Procurar por processos xrdp-sesman rodando como usuários (não root)
                    if 'xrdp-sesman' in proc.info['name'].lower():
                        username = proc.info['username']

                        # Ignorar processos root (são os daemons principais)
                        if username != 'root' and username not in seen_users:
                            # Este é um processo de sessão de usuário
                            try:
                                # Verificar se tem conexões estabelecidas
                                proc_connections = proc.connections(kind='inet')

                                for conn in proc_connections:
                                    if conn.status == 'ESTABLISHED':
                                        connections.append({
                                            'username': username,
                                            'session_id': str(proc.info['pid']),
                                            'remote_ip': conn.raddr.ip if conn.raddr else 'unknown',
                                            'port': conn.laddr.port if conn.laddr else 0
                                        })
                                        seen_users.add(username)
                                        break
                            except (psutil.AccessDenied, AttributeError):
                                pass

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            # Método 2: Verificar via loginctl (sessões gráficas)
            try:
                result = subprocess.run(
                    ['loginctl', 'list-sessions', '--no-legend'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )

                if result.returncode == 0:
                    for line in result.stdout.strip().split('\n'):
                        if not line:
                            continue

                        parts = line.split()
                        if len(parts) >= 3:
                            session_id = parts[0]
                            username = parts[2]

                            # Verificar detalhes da sessão
                            session_details = subprocess.run(
                                ['loginctl', 'show-session', session_id],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )

                            if session_details.returncode == 0:
                                session_info = session_details.stdout

                                # Verificar se é sessão xrdp (tem display remoto)
                                if 'Remote=yes' in session_info or 'xrdp' in session_info.lower():
                                    if username not in seen_users:
                                        connections.append({
                                            'username': username,
                                            'session_id': session_id,
                                            'remote_ip': 'unknown',
                                            'port': 0
                                        })
                                        seen_users.add(username)

            except (subprocess.TimeoutExpired, FileNotFoundError):
                # loginctl não disponível ou timeout
                pass

        except Exception as e:
            logger.error(f"Error getting RDP connections: {e}")

        return connections

    def get_user_session(self, username: str) -> Optional[SessionInfo]:
        """Obtém informações da sessão de um usuário específico"""
        for session in self.get_active_sessions():
            if session.username == username:
                return session

        return None

    def is_user_connected(self, username: str) -> bool:
        """Verifica se um usuário está conectado"""
        return self.get_user_session(username) is not None

    def get_session_count(self) -> int:
        """Retorna número de sessões ativas"""
        return len(self.get_active_sessions())

    def get_ip_address(self) -> str:
        """Obtém endereço IP do servidor"""
        if self._ip_cache:
            return self._ip_cache
        try:
            # Criar socket para determinar IP principal
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            self._ip_cache = ip
            return ip

        except Exception as e:
            logger.error(f"Error getting IP address: {e}")

            # Tentar via hostname
            try:
                hostname = socket.gethostname()
                self._ip_cache = socket.gethostbyname(hostname)
                return self._ip_cache
            except:
                return "127.0.0.1"

    def get_all_network_ips(self) -> List[str]:
        """Retorna todos os endereços IP do servidor"""
        ips = []

        try:
            import netifaces

            for interface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(interface)

                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        ip = addr['addr']
                        if ip != '127.0.0.1':
                            ips.append(ip)

        except ImportError:
            # netifaces não disponível, usar método alternativo
            for interface, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET and snic.address != '127.0.0.1':
                        ips.append(snic.address)

        except Exception as e:
            logger.error(f"Error getting IP addresses: {e}")

        return ips if ips else ["127.0.0.1"]

    def disconnect_user(self, username: str) -> bool:
        """Request a graceful xrdp session termination.

        xrdp does not expose a stable detach-only CLI. Terminating the login
        session is safer than pretending a disconnect succeeded.
        """
        try:
            session = self.get_user_session(username)

            if not session:
                logger.warning(f"No active session for {username}")
                return False

            if not session.session_id:
                return False
            result = subprocess.run(
                ['loginctl', 'terminate-session', session.session_id],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.invalidate()
                logger.info(f"Session {session.session_id} for {username} terminated")
                return True
            logger.error("loginctl failed for %s: %s", username, result.stderr.strip())
            return False

        except Exception as e:
            logger.error(f"Error disconnecting {username}: {e}")
            return False

    def kill_user_session(self, username: str) -> bool:
        """Encerra forçadamente a sessão de um usuário"""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    if proc.info['username'] == username:
                        proc.terminate()
                        processes.append(proc)

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if processes:
                _, alive = psutil.wait_procs(processes, timeout=5)
                for proc in alive:
                    try:
                        proc.kill()
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                self.invalidate()
                logger.info(f"Session for {username} terminated")

            return bool(processes)

        except Exception as e:
            logger.error(f"Error terminating session for {username}: {e}")
            return False

    def get_system_stats(self) -> Dict:
        """Retorna estatísticas do sistema"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_used_gb': memory.used / (1024**3),
                'memory_total_gb': memory.total / (1024**3),
                'disk_percent': disk.percent,
                'disk_used_gb': disk.used / (1024**3),
                'disk_total_gb': disk.total / (1024**3),
                'active_sessions': self.get_session_count()
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}

    def check_port_status(self, port: int) -> bool:
        """Verifica se uma porta está em uso"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0

        except Exception as e:
            logger.error(f"Error checking port {port}: {e}")
            return False

    def get_connection_history(self, username: str, limit: int = 10) -> List[Dict]:
        """
        Obtém histórico de conexões de um usuário

        TODO: Implementar persistência do histórico
        """
        # Por enquanto retornar lista vazia
        # Futuramente implementar leitura de logs
        return []
