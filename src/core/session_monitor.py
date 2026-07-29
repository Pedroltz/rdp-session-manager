#!/usr/bin/env python3
"""
RDP session monitoring module
"""

import subprocess
import logging
import psutil
import socket
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SessionInfo:
    """Information from an RDP session"""

    def __init__(self, username: str, session_id: str = "", ip_address: str = "",
                 port: int = 0, connected: bool = False, start_time: datetime = None):
        self.username = username
        self.session_id = session_id
        self.ip_address = ip_address
        self.port = port
        self.connected = connected
        self.start_time = start_time or datetime.now()

    def to_dict(self) -> Dict:
        """Converts to dictionary"""
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
        """Returns session duration in seconds"""
        if self.start_time:
            return int((datetime.now() - self.start_time).total_seconds())
        return 0


class SessionMonitor:
    """RDP session monitor"""

    def __init__(self):
        self.sessions = {}

    def get_active_sessions(self) -> List[SessionInfo]:
        """Returns list of active sessions"""
        sessions = []

        try:
            # Check active RDP connections
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
            logger.error(f"Error getting active sessions: {e}")

        return sessions

    def _get_rdp_connections(self) -> List[Dict]:
        """Gets active RDP connections from the system"""
        connections = []
        seen_users = set()

        try:
            # Method 1: Check xrdp-sesman processes of specific users
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    # Search for xrdp-sesman processes running as users (not root)
                    if 'xrdp-sesman' in proc.info['name'].lower():
                        username = proc.info['username']

                        # Ignore root processes (these are the main daemons)
                        if username != 'root' and username not in seen_users:
                            # This is a user session process
                            try:
                                # Check if you have established connections
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

            # Method 2: Check via loginctl (graphical sessions)
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

                            # Check session details
                            session_details = subprocess.run(
                                ['loginctl', 'show-session', session_id],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )

                            if session_details.returncode == 0:
                                session_info = session_details.stdout

                                # Check if it is an xrdp session (has a remote display)
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
                # loginctl not available or timeout
                pass

        except Exception as e:
            logger.error(f"Error getting RDP connections: {e}")

        return connections

    def get_user_session(self, username: str) -> Optional[SessionInfo]:
        """Gets session information for a specific user"""
        for session in self.get_active_sessions():
            if session.username == username:
                return session

        return None

    def is_user_connected(self, username: str) -> bool:
        """Checks if a user is logged in"""
        return self.get_user_session(username) is not None

    def get_session_count(self) -> int:
        """Returns number of active sessions"""
        return len(self.get_active_sessions())

    def get_ip_address(self) -> str:
        """Get server IP address"""
        try:
            # Create socket to determine main IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip

        except Exception as e:
            logger.error(f"Error obtaining IP: {e}")

            # Try via hostname
            try:
                hostname = socket.gethostname()
                return socket.gethostbyname(hostname)
            except:
                return "127.0.0.1"

    def get_all_network_ips(self) -> List[str]:
        """Returns all server IP addresses"""
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
            # netifaces not available, use alternative method
            for interface, snics in psutil.net_if_addrs().items():
                for snic in snics:
                    if snic.family == socket.AF_INET and snic.address != '127.0.0.1':
                        ips.append(snic.address)

        except Exception as e:
            logger.error(f"Error obtaining IPs: {e}")

        return ips if ips else ["127.0.0.1"]

    def disconnect_user(self, username: str) -> bool:
        """Disconnects a user"""
        try:
            session = self.get_user_session(username)

            if not session:
                logger.warning(f"No active sessions for {username}")
                return False

            # Disconnect via system command
            # TODO: Implement real disconnection
            logger.info(f"Disconnecting user {username}")

            return True

        except Exception as e:
            logger.error(f"Error disconnecting {username}: {e}")
            return False

    def kill_user_session(self, username: str) -> bool:
        """Forcibly ends a user's session"""
        try:
            # Get user processes
            killed = False

            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    if proc.info['username'] == username:
                        proc.kill()
                        killed = True

                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if killed:
                logger.info(f"{username} session closed")

            return killed

        except Exception as e:
            logger.error(f"Error closing session of {username}: {e}")
            return False

    def get_system_stats(self) -> Dict:
        """Returns system statistics"""
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
        """Checks if a port is in use"""
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
        Gets a user's connection history

        TODO: Implement history persistence
        """
        # For now return empty list
        # In the future implement log reading
        return []
