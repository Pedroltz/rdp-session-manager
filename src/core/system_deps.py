#!/usr/bin/env python3
"""
Módulo de gerenciamento de dependências do sistema
"""

import subprocess
import logging
from typing import Tuple, Optional, Callable

from utils.polkit import get_privilege_command

logger = logging.getLogger(__name__)


class SystemDependencies:
    """Gerenciador de dependências do sistema"""

    # Pacotes necessários para o funcionamento básico
    # Formato: distro -> packages
    REQUIRED_PACKAGES = {
        'xrdp': {
            'name': 'xrdp',
            'packages': {
                'debian': ['xrdp', 'xorgxrdp'],
                'arch': ['xrdp']
            },
            'description': 'RDP Server (Remote Desktop Protocol)',
            'service': 'xrdp',
            'critical': True
        },
        'freerdp': {
            'name': 'FreeRDP',
            'packages': {
                'debian': ['freerdp3-x11'],
                'arch': ['freerdp']
            },
            'description': 'Cliente RDP (Remote Desktop Protocol)',
            'service': None,
            'critical': False  # Não é crítico para criar usuários, só para conectar
        },
        'x11': {
            'name': 'X11',
            'packages': {
                'debian': ['xorg', 'x11-xserver-utils'],
                'arch': ['xorg-server', 'xorg-server-utils']
            },
            'description': 'Sistema de janelas X11',
            'service': None,
            'critical': True
        }
    }

    def __init__(self):
        self.distro = self._detect_distro()
        self.pkg_manager = self._get_package_manager()

    def _detect_distro(self) -> str:
        """Detecta a distribuição Linux"""
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('ID='):
                        distro_id = line.split('=')[1].strip().strip('"')
                        # Mapear para categorias principais
                        if distro_id in ['arch', 'manjaro', 'endeavouros', 'cachyos']:
                            return 'arch'
                        elif distro_id in ['debian', 'ubuntu', 'linuxmint', 'pop']:
                            return 'debian'
                        else:
                            return 'debian'  # default
        except:
            return 'debian'  # default

    def _get_package_manager(self) -> str:
        """Retorna o gerenciador de pacotes baseado na distro"""
        return 'pacman' if self.distro == 'arch' else 'apt'

    def is_package_installed(self, package_name: str) -> bool:
        """Verifica se um pacote está instalado"""
        try:
            if self.pkg_manager == 'pacman':
                result = subprocess.run(
                    ['pacman', '-Q', package_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            else:  # apt/dpkg
                result = subprocess.run(
                    ['dpkg', '-l', package_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0 and 'ii' in result.stdout

        except Exception as e:
            logger.error(f"Error checking package {package_name}: {e}")
            return False

    def check_dependencies(self) -> Tuple[bool, list, list]:
        """
        Verifica todas as dependências do sistema

        Returns:
            Tuple (tudo_ok, faltando, instalados)
        """
        missing = []
        installed = []

        for dep_id, dep_info in self.REQUIRED_PACKAGES.items():
            # Verificação especial para FreeRDP (usa comando xfreerdp)
            if dep_id == 'freerdp':
                if self.is_freerdp_installed():
                    installed.append(dep_id)
                    logger.info(f"OK {dep_info['name']} is installed")
                else:
                    if dep_info['critical']:
                        missing.append(dep_id)
                    logger.info(f"ℹ {dep_info['name']} is not installed (optional)")
                continue

            # Obter pacotes corretos para a distro atual
            packages = dep_info['packages'].get(self.distro, dep_info['packages'].get('debian', []))
            if not packages:
                logger.warning(f"No package defined for {dep_id} on {self.distro}")
                continue

            # Verifica o pacote principal
            main_package = packages[0]

            if self.is_package_installed(main_package):
                installed.append(dep_id)
                logger.info(f"OK {dep_info['name']} is installed")
            else:
                if dep_info['critical']:
                    missing.append(dep_id)
                    logger.warning(f"X {dep_info['name']} is NOT installed")

        return len(missing) == 0, missing, installed

    def install_package(self, dep_id: str, progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        Instala um pacote de dependência

        Args:
            dep_id: ID da dependência (ex: 'xrdp')
            progress_callback: Função callback(progress, message)

        Returns:
            Tuple (sucesso, mensagem)
        """
        def log(progress, message):
            if progress_callback:
                progress_callback(progress, message)
            logger.info(message)

        if dep_id not in self.REQUIRED_PACKAGES:
            return False, f"Unknown dependency '{dep_id}'"

        dep_info = self.REQUIRED_PACKAGES[dep_id]

        # Obter pacotes corretos para a distro atual
        packages = dep_info['packages'].get(self.distro, dep_info['packages'].get('debian', []))
        if not packages:
            return False, f"No package defined for {dep_id} on {self.distro}"

        # Verificar se já está instalado
        if self.is_package_installed(packages[0]):
            msg = f"{dep_info['name']} is already installed"
            log(100, f"OK {msg}")
            return True, msg

        try:
            log(5, f"→ Installing {dep_info['name']}...")
            log(5, f"  Description: {dep_info['description']}")
            log(5, f"  Packages: {', '.join(packages)}")
            log(5, "")

            # Obter comando de elevação apropriado (pkexec ou sudo)
            priv_method, priv_cmd = get_privilege_command()
            auth_msg = "pkexec" if priv_method == "pkexec" else "sudo"

            log(10, f"  WARNING You will be asked to authenticate ({auth_msg})")
            log(10, "")

            # Usar script helper que agrupa update + install
            from pathlib import Path
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            install_script = script_dir / "install-packages.sh"

            log(15, "→ Running integrated installation...")
            log(15, "")

            cmd = priv_cmd + [str(install_script)] + packages

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Ler saída linha por linha
            progress = 30
            for line in process.stdout:
                line = line.rstrip()
                if line:
                    # Filtrar e formatar saída do apt
                    if any(kw in line for kw in ['Unpacking', 'Preparing', 'Setting up', 'Processing']):
                        log(progress, f"  {line}")
                        progress = min(progress + 2, 90)
                    elif 'Get:' in line or 'Fetched' in line:
                        log(progress, f"  {line}")
                    elif 'Reading' in line or 'Building' in line:
                        log(progress, f"  {line}")
                    elif line.startswith('E:') or line.startswith('Err:'):
                        log(progress, f"  X {line}")
                    else:
                        logger.debug(f"apt: {line}")

            returncode = process.wait(timeout=600)  # 10 minutos para xrdp

            if returncode != 0:
                error_msg = f"Failed to install {dep_info['name']} (exit code: {returncode})"
                logger.error(error_msg)
                log(progress, f"X {error_msg}")
                return False, error_msg

            log(90, "")
            log(90, f"  OK {dep_info['name']} installed successfully")

            # Iniciar serviço se necessário
            if dep_info['service']:
                log(95, f"→ Starting service {dep_info['service']}...")

                # Habilitar serviço
                subprocess.run(
                    priv_cmd + ['/usr/bin/systemctl', 'enable', dep_info['service']],
                    capture_output=True,
                    timeout=10
                )

                # Iniciar serviço
                start_result = subprocess.run(
                    priv_cmd + ['/usr/bin/systemctl', 'start', dep_info['service']],
                    capture_output=True,
                    timeout=10
                )

                if start_result.returncode == 0:
                    log(98, f"  OK Service {dep_info['service']} started")
                else:
                    log(98, f"  WARNING Failed to start service {dep_info['service']}")

            log(100, "")
            log(100, f"OK {dep_info['name']} configured and ready to use!")

            return True, f"{dep_info['name']} installed successfully"

        except subprocess.TimeoutExpired:
            error_msg = f"Installation of {dep_info['name']} timed out"
            logger.error(error_msg)
            log(0, f"X {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Error installing {dep_info['name']}: {e}"
            logger.error(error_msg)
            log(0, f"X {error_msg}")
            return False, error_msg

    def ensure_dependencies(self, progress_callback: Optional[Callable] = None) -> Tuple[bool, str]:
        """
        Garante que todas as dependências críticas estejam instaladas

        Returns:
            Tuple (sucesso, mensagem)
        """
        all_ok, missing, installed = self.check_dependencies()

        if all_ok:
            return True, "All dependencies are installed"

        # Instalar dependências faltantes
        for dep_id in missing:
            success, msg = self.install_package(dep_id, progress_callback)
            if not success:
                return False, f"Failed to install {dep_id}: {msg}"

        return True, "Dependencies installed successfully"

    def is_service_running(self, service_name: str) -> bool:
        """Verifica se um serviço systemd está rodando"""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and 'active' in result.stdout

        except Exception as e:
            logger.error(f"Error checking service {service_name}: {e}")
            return False

    def is_xrdp_ready(self) -> bool:
        """Verifica se xrdp está instalado e funcionando"""
        return self.is_package_installed('xrdp')

    def is_freerdp_installed(self) -> bool:
        """Verifica se FreeRDP está instalado"""
        import shutil
        # Verificar se o comando xfreerdp3 ou xfreerdp está disponível
        return shutil.which('xfreerdp3') is not None or shutil.which('xfreerdp') is not None

    def get_freerdp_command(self) -> str:
        """Retorna o comando FreeRDP disponível"""
        import shutil
        if shutil.which('xfreerdp3'):
            return 'xfreerdp3'
        elif shutil.which('xfreerdp'):
            return 'xfreerdp'
        return None

    def get_xrdp_status(self) -> dict:
        """Retorna status detalhado do xrdp"""
        return {
            'installed': self.is_package_installed('xrdp'),
            'service_running': self.is_service_running('xrdp'),
            'port_3389_open': self._check_port_open(3389)
        }

    def _check_port_open(self, port: int) -> bool:
        """Verifica se uma porta está aberta"""
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result == 0
        except:
            return False
