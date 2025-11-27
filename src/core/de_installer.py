#!/usr/bin/env python3
"""
Módulo de instalação de ambientes desktop
"""

import subprocess
import logging
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class DEInstaller:
    """Instalador de ambientes desktop"""

    # Pacotes necessários para cada DE por distribuição
    DE_PACKAGES = {
        'gnome': {
            'name': 'GNOME',
            'packages': {
                'debian': [
                    'gnome-session',
                    'gnome-shell',
                    'gnome-terminal',
                    'nautilus',
                    'gnome-control-center',
                    'gnome-tweaks'
                ],
                'arch': [
                    'gnome',
                    'gnome-shell',
                    'gnome-terminal',
                    'nautilus',
                    'gnome-control-center',
                    'gnome-tweaks'
                ]
            },
            'size_mb': 1200,
            'startup_cmd': 'gnome-session'
        },
        'xfce': {
            'name': 'XFCE',
            'packages': {
                'debian': [
                    'xfce4',
                    'xfce4-goodies',
                    'xfce4-terminal',
                    'thunar'
                ],
                'arch': [
                    'xfce4',
                    'xfce4-goodies',
                    'xfce4-terminal',
                    'thunar'
                ]
            },
            'size_mb': 400,
            'startup_cmd': 'startxfce4'
        },
        'xfce4': {  # Alias para xfce
            'name': 'XFCE',
            'packages': {
                'debian': [
                    'xfce4',
                    'xfce4-goodies',
                    'xfce4-terminal',
                    'thunar'
                ],
                'arch': [
                    'xfce4',
                    'xfce4-goodies',
                    'xfce4-terminal',
                    'thunar'
                ]
            },
            'size_mb': 400,
            'startup_cmd': 'startxfce4'
        },
        'kde': {
            'name': 'KDE Plasma',
            'packages': {
                'debian': [
                    'kde-plasma-desktop',
                    'plasma-workspace',
                    'konsole',
                    'dolphin',
                    'systemsettings'
                ],
                'arch': [
                    'plasma-desktop',
                    'plasma-workspace',
                    'konsole',
                    'dolphin',
                    'systemsettings'
                ]
            },
            'size_mb': 1500,
            'startup_cmd': 'startplasma-x11'
        },
        'plasma': {  # Alias para kde
            'name': 'KDE Plasma',
            'packages': {
                'debian': [
                    'kde-plasma-desktop',
                    'plasma-workspace',
                    'konsole',
                    'dolphin',
                    'systemsettings'
                ],
                'arch': [
                    'plasma-desktop',
                    'plasma-workspace',
                    'konsole',
                    'dolphin',
                    'systemsettings'
                ]
            },
            'size_mb': 1500,
            'startup_cmd': 'startplasma-x11'
        },
        'mate': {
            'name': 'MATE',
            'packages': {
                'debian': [
                    'mate-desktop-environment',
                    'mate-terminal',
                    'caja'
                ],
                'arch': [
                    'mate',
                    'mate-terminal',
                    'caja'
                ]
            },
            'size_mb': 600,
            'startup_cmd': 'mate-session'
        },
        'cinnamon': {
            'name': 'Cinnamon',
            'packages': {
                'debian': [
                    'cinnamon-desktop-environment',
                    'cinnamon',
                    'nemo'
                ],
                'arch': [
                    'cinnamon',
                    'nemo'
                ]
            },
            'size_mb': 800,
            'startup_cmd': 'cinnamon-session'
        },
        'lxde': {
            'name': 'LXDE',
            'packages': {
                'debian': [
                    'lxde',
                    'lxterminal',
                    'pcmanfm'
                ],
                'arch': [
                    'lxde-common',
                    'lxterminal',
                    'pcmanfm'
                ]
            },
            'size_mb': 250,
            'startup_cmd': 'startlxde'
        },
        'lxqt': {
            'name': 'LXQt',
            'packages': {
                'debian': [
                    'lxqt',
                    'qterminal',
                    'pcmanfm-qt'
                ],
                'arch': [
                    'lxqt',
                    'qterminal',
                    'pcmanfm-qt'
                ]
            },
            'size_mb': 350,
            'startup_cmd': 'startlxqt'
        }
    }

    def __init__(self):
        self.distro_info = self._detect_distro()
        self.distro_type = self._get_distro_type()
        self.pkg_manager = 'pacman' if self.distro_type == 'arch' else 'apt'

    def _detect_distro(self) -> Dict:
        """Detecta a distribuição Linux"""
        try:
            with open('/etc/os-release', 'r') as f:
                lines = f.readlines()

            info = {}
            for line in lines:
                if '=' in line:
                    key, value = line.strip().split('=', 1)
                    info[key] = value.strip('"')

            return {
                'id': info.get('ID', 'unknown'),
                'version': info.get('VERSION_ID', 'unknown'),
                'name': info.get('NAME', 'Unknown')
            }

        except Exception as e:
            logger.error(f"Erro ao detectar distribuição: {e}")
            return {'id': 'unknown', 'version': 'unknown', 'name': 'Unknown'}

    def _get_distro_type(self) -> str:
        """Retorna o tipo de distribuição (arch ou debian)"""
        distro_id = self.distro_info['id']
        if distro_id in ['arch', 'manjaro', 'endeavouros', 'cachyos']:
            return 'arch'
        elif distro_id in ['debian', 'ubuntu', 'linuxmint', 'pop']:
            return 'debian'
        else:
            return 'debian'  # default

    def get_available_des(self) -> List[Dict]:
        """Retorna lista de DEs disponíveis para instalação"""
        des = []

        for de_id, de_info in self.DE_PACKAGES.items():
            # Evitar aliases duplicados
            if de_id in ['xfce4', 'plasma']:
                continue

            des.append({
                'id': de_id,
                'name': de_info['name'],
                'size_mb': de_info['size_mb'],
                'installed': self.is_de_installed(de_id)
            })

        return sorted(des, key=lambda x: x['size_mb'])

    def is_de_installed(self, de_id: str) -> bool:
        """Verifica se um DE está instalado"""
        if de_id not in self.DE_PACKAGES:
            return False

        de_info = self.DE_PACKAGES[de_id]

        # Obter pacotes corretos para a distro atual
        packages = de_info['packages'].get(self.distro_type, de_info['packages'].get('debian', []))
        if not packages:
            return False

        main_package = packages[0]

        try:
            if self.pkg_manager == 'pacman':
                result = subprocess.run(
                    ['pacman', '-Q', main_package],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0
            else:  # dpkg
                result = subprocess.run(
                    ['dpkg', '-l', main_package],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return result.returncode == 0 and 'ii' in result.stdout

        except Exception as e:
            logger.error(f"Erro ao verificar instalação de {de_id}: {e}")
            return False

    def install_de(self, de_id: str, progress_callback=None) -> Tuple[bool, str]:
        """
        Instala um ambiente desktop

        Args:
            de_id: ID do desktop environment
            progress_callback: Função de callback para progresso (progress, message)

        Returns:
            Tuple (sucesso, mensagem)
        """
        def log(progress, message):
            if progress_callback:
                progress_callback(progress, message)
            logger.info(message)

        if de_id not in self.DE_PACKAGES:
            return False, f"Desktop environment '{de_id}' não suportado"

        if self.is_de_installed(de_id):
            msg = f"{self.DE_PACKAGES[de_id]['name']} já está instalado"
            logger.info(msg)
            log(100, f"OK {msg}")
            return True, msg

        de_info = self.DE_PACKAGES[de_id]

        # Obter pacotes corretos para a distro atual
        packages = de_info['packages'].get(self.distro_type, de_info['packages'].get('debian', []))
        if not packages:
            return False, f"Nenhum pacote definido para {de_id} na distro {self.distro_type}"

        try:
            log(5, f"→ Verificando espaço em disco...")

            # Verificar espaço em disco
            has_space, required, available = self.check_disk_space(de_id)
            if not has_space:
                error_msg = f"Espaço insuficiente. Necessário: {required}MB, Disponível: {available}MB"
                log(0, f"X {error_msg}")
                return False, error_msg

            log(5, f"  OK Espaço disponível: {available}MB (necessário: {required}MB)")
            log(5, "")

            # Atualizar cache do gerenciador de pacotes
            log(10, "→ Atualizando cache de pacotes...")
            log(10, "  AVISO Você será solicitado a autenticar (pkexec)")

            if self.pkg_manager == 'pacman':
                log(10, "  $ pkexec pacman -Sy")
                update_result = subprocess.run(
                    ['pkexec', '/usr/bin/pacman', '-Sy'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )
            else:  # apt
                log(10, "  $ pkexec apt-get update")
                update_result = subprocess.run(
                    ['pkexec', '/usr/bin/apt-get', 'update'],
                    capture_output=True,
                    text=True,
                    timeout=120
                )

            if update_result.returncode != 0:
                logger.warning(f"Update retornou código {update_result.returncode}")
                log(10, f"  AVISO Aviso: Update retornou código {update_result.returncode}")
            else:
                log(15, "  OK Cache atualizado com sucesso")

            log(15, "")

            # Instalar pacotes
            log(20, f"→ Instalando {de_info['name']}...")
            log(20, f"  Pacotes: {', '.join(packages)}")
            log(20, "")
            log(20, "  AVISO Você será solicitado a autenticar novamente")

            if self.pkg_manager == 'pacman':
                log(20, f"  $ pkexec pacman -S --noconfirm {' '.join(packages)}")
                log(20, "")
                log(30, "→ Baixando e instalando pacotes...")
            else:  # apt
                log(20, f"  $ pkexec apt-get install -y {' '.join(packages)}")
                log(20, "")
                log(30, "→ Baixando e instalando pacotes...")
                log(30, "  (pkexec bloqueia saída - monitorando /var/log/apt/term.log)")
            log(30, "")

            # pkexec NÃO permite capturar stdout/stderr via pipe
            # Solução: Monitorar arquivos de log em tempo real
            import time
            import os

            if self.pkg_manager == 'pacman':
                log_file = '/var/log/pacman.log'
                cmd = ['pkexec', '/usr/bin/pacman', '-S', '--noconfirm'] + packages
            else:  # apt
                log_file = '/var/log/apt/term.log'
                cmd = ['pkexec', '/usr/bin/apt-get', 'install', '-y', '--no-install-recommends'] + packages

            try:
                initial_size = os.path.getsize(log_file)
            except:
                initial_size = 0

            # Executar em background (stdout vai para /dev/null pois pkexec bloqueia)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Monitorar arquivo de log em tempo real
            progress = 30
            last_position = initial_size
            last_log_time = time.time()

            try:
                while process.poll() is None:  # Enquanto processo está rodando
                    time.sleep(1)  # Check a cada 1 segundo

                    # A cada 5 segundos, mostrar que está vivo
                    if time.time() - last_log_time > 5:
                        log(progress, "  ... instalando (processo rodando)...")
                        last_log_time = time.time()

                    try:
                        with open(log_file, 'r') as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            last_position = f.tell()

                            for line in new_lines:
                                line = line.rstrip()
                                if line and progress < 90:
                                    if self.pkg_manager == 'pacman':
                                        # Filtrar linhas relevantes do pacman
                                        if any(kw in line for kw in ['installing', 'upgrading', 'downloading']):
                                            log(progress, f"  {line[:100]}")
                                            progress = min(progress + 2, 90)
                                            last_log_time = time.time()
                                        elif 'error' in line.lower():
                                            log(progress, f"  X {line[:150]}")
                                            last_log_time = time.time()
                                    else:  # apt
                                        # Filtrar linhas relevantes do apt
                                        if any(kw in line for kw in ['Desempacotando', 'Unpacking', 'Preparando', 'Preparing', 'Configurando', 'Setting up']):
                                            log(progress, f"  {line[:100]}")
                                            progress = min(progress + 2, 90)
                                            last_log_time = time.time()
                                        elif any(kw in line for kw in ['Get:', 'Obter:', 'Fetched', 'Baixados']):
                                            if 'Get:' in line or 'Obter:' in line:
                                                log(progress, f"  {line[:100]}")
                                            progress = min(progress + 1, 90)
                                            last_log_time = time.time()
                                        elif any(kw in line for kw in ['erro', 'error', 'E:', 'Err:']):
                                            log(progress, f"  X {line[:150]}")
                                            last_log_time = time.time()
                    except Exception as e:
                        logger.debug(f"Erro lendo log: {e}")

                # Processo terminou, pegar código de retorno
                returncode = process.wait()

                if returncode != 0:
                    error_msg = f"Falha na instalação (código: {returncode})"
                    logger.error(error_msg)
                    log(progress, f"X {error_msg}")
                    return False, error_msg

            except Exception as e:
                logger.error(f"Erro durante instalação: {e}")
                try:
                    process.kill()
                except:
                    pass
                raise

            log(90, "")
            log(90, "  OK Pacotes instalados com sucesso")
            log(95, f"  OK {de_info['name']} configurado")
            log(100, "")
            log(100, f"OK {de_info['name']} instalado com sucesso!")

            logger.info(f"{de_info['name']} instalado com sucesso")
            return True, f"{de_info['name']} instalado com sucesso"

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout na instalação de {de_info['name']} (30 minutos)"
            logger.error(error_msg)
            log(0, f"X {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Erro ao instalar {de_info['name']}: {e}"
            logger.error(error_msg)
            log(0, f"X {error_msg}")
            return False, error_msg

    def get_de_info(self, de_id: str) -> Optional[Dict]:
        """Retorna informações sobre um DE específico"""
        if de_id in self.DE_PACKAGES:
            info = self.DE_PACKAGES[de_id].copy()
            info['id'] = de_id
            info['installed'] = self.is_de_installed(de_id)
            return info

        return None

    def get_de_startup_command(self, de_id: str) -> Optional[str]:
        """Retorna o comando de inicialização de um DE"""
        if de_id in self.DE_PACKAGES:
            return self.DE_PACKAGES[de_id]['startup_cmd']

        return None

    def check_disk_space(self, de_id: str) -> Tuple[bool, int, int]:
        """
        Verifica se há espaço em disco suficiente

        Returns:
            Tuple (suficiente, necessário_mb, disponível_mb)
        """
        import shutil

        if de_id not in self.DE_PACKAGES:
            return False, 0, 0

        required_mb = self.DE_PACKAGES[de_id]['size_mb']

        try:
            stat = shutil.disk_usage('/')
            available_mb = stat.free // (1024 * 1024)

            # Adicionar 20% de margem de segurança
            required_with_margin = int(required_mb * 1.2)

            return available_mb >= required_with_margin, required_with_margin, available_mb

        except Exception as e:
            logger.error(f"Erro ao verificar espaço em disco: {e}")
            return False, required_mb, 0

