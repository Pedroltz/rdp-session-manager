#!/usr/bin/env python3
"""
Módulo de monitoramento de sessões RDP
"""

import subprocess
import logging
import psutil
import socket
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionInfo:
    """Informações de uma sessão RDP"""

    def __init__(self, username: str, session_id: str = "", ip_address: str = "",
                 port: int = 0, connected: bool = False, start_time: datetime = None):
        self.username = username
        self.session_id = session_id
        self.ip_address = ip_address
        self.port = port
        self.connected = connected
        self.start_time = start_time or datetime.now()

    def to_dict(self) -> Dict:
        """Converte para dicionário"""
        return {
            'username': self.username,
            'session_id': self.session_id,
            'ip_address': self.ip_address,
            'port': self.port,
            'connected': self.connected,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'duration': self.get_duration()
        }

    def get_duration(self) -> int:
        """Retorna duração da sessão em segundos"""
        if self.start_time:
            return int((datetime.now() - self.start_time).total_seconds())
        return 0


class SessionMonitor:
    """Monitor de sessões RDP"""

    def __init__(self):
        self.sessions = {}

    def get_active_sessions(self) -> List[SessionInfo]:
        """Retorna lista de sessões ativas"""
        sessions = []

        try:
            # Verificar conexões RDP ativas
            connections = self._get_rdp_connections()

            for conn in connections:
                session = SessionInfo(
                    username=conn.get('username', 'unknown'),
                    session_id=conn.get('session_id', ''),
                    ip_address=conn.get('remote_ip', ''),
                    port=conn.get('port', 0),
                    connected=True
                )
                sessions.append(session)

        except Exception as e:
            logger.error(f"Erro ao obter sessões ativas: {e}")

        return sessions

    def _get_rdp_connections(self) -> List[Dict]:
        """Obtém conexões RDP ativas do sistema"""
        connections = []

        try:
            # Verificar processos xrdp
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    if 'xrdp' in proc.info['name'].lower():
                        # Obter conexões do processo
                        try:
                            proc_connections = proc.connections(kind='inet')

                            for conn in proc_connections:
                                if conn.status == 'ESTABLISHED':
                                    connections.append({
                                        'username': proc.info['username'],
                                        'session_id': str(proc.info['pid']),
                                        'remote_ip': conn.raddr.ip if conn.raddr else 'unknown',
                                        'port': conn.laddr.port if conn.laddr else 0
                                    })
                        except (psutil.AccessDenied, AttributeError):
                            # Processo não tem permissão ou não tem conexões
                            pass

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

        except Exception as e:
            logger.error(f"Erro ao obter conexões RDP: {e}")

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
        try:
            # Criar socket para determinar IP principal
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip

        except Exception as e:
            logger.error(f"Erro ao obter IP: {e}")

            # Tentar via hostname
            try:
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
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
            logger.error(f"Erro ao obter IPs: {e}")

        return ips if ips else ["127.0.0.1"]

    def disconnect_user(self, username: str) -> bool:
        """Desconecta um usuário"""
        try:
            session = self.get_user_session(username)

            if not session:
                logger.warning(f"Nenhuma sessão ativa para {username}")
                return False

            # Desconectar via comando do sistema
            # TODO: Implementar desconexão real
            logger.info(f"Desconectando usuário {username}")

            return True

        except Exception as e:
            logger.error(f"Erro ao desconectar {username}: {e}")
            return False

    def kill_user_session(self, username: str) -> bool:
        """Encerra forçadamente a sessão de um usuário"""
        try:
            # Obter processos do usuário
            killed = False

            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    if proc.info['username'] == username:
                        proc.kill()
                        killed = True

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if killed:
                logger.info(f"Sessão de {username} encerrada")

            return killed

        except Exception as e:
            logger.error(f"Erro ao encerrar sessão de {username}: {e}")
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
            logger.error(f"Erro ao obter estatísticas: {e}")
            return {}

    def check_port_status(self, port: int) -> bool:
        """Verifica se uma porta está em uso"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0

        except Exception as e:
            logger.error(f"Erro ao verificar porta {port}: {e}")
            return False

    def get_connection_history(self, username: str, limit: int = 10) -> List[Dict]:
        """
        Obtém histórico de conexões de um usuário

        TODO: Implementar persistência do histórico
        """
        # Por enquanto retornar lista vazia
        # Futuramente implementar leitura de logs
        return []
