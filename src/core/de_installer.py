#!/usr/bin/env python3
"""
Desktop environment installation module
"""

import subprocess
import logging
from typing import Dict, List, Optional, Tuple

from utils.polkit import get_privilege_command, has_display

logger = logging.getLogger(__name__)


class DEInstaller:
    """Desktop Environment Installer"""

    # Packages required for each DE (Debian/Ubuntu)
    DE_PACKAGES = {
        'gnome': {
            'name': 'GNOME',
            'packages': [
                'gnome-session',
                'gnome-shell',
                'gnome-terminal',
                'nautilus',
                'gnome-control-center',
                'gnome-tweaks',
                'mutter',              # Window manager
                'gnome-settings-daemon',
                'dbus-x11'
            ],
            'size_mb': 1400,
            'startup_cmd': 'gnome-session'
        },
        'xfce': {
            'name': 'XFCE',
            'packages': [
                'xfce4',
                'xfce4-goodies',
                'xfce4-terminal',
                'thunar',
                'xfwm4',               # Window manager
                'xfce4-settings',
                'dbus-x11'
            ],
            'size_mb': 450,
            'startup_cmd': 'startxfce4'
        },
        'xfce4': { # Alias ​​for xfce
            'name': 'XFCE',
            'packages': [
                'xfce4',
                'xfce4-goodies',
                'xfce4-terminal',
                'thunar',
                'xfwm4',
                'xfce4-settings',
                'dbus-x11'
            ],
            'size_mb': 450,
            'startup_cmd': 'startxfce4'
        },
        'kde': {
            'name': 'KDE Plasma',
            'packages': [
                'kde-plasma-desktop',
                'plasma-workspace',
                'kwin-x11',            # Window manager (essential!)
                'konsole',
                'dolphin',
                'systemsettings',
                'plasma-desktop',
                'dbus-x11'
            ],
            'size_mb': 1800,
            'startup_cmd': 'startplasma-x11'
        },
        'plasma': { # Alias ​​for kde
            'name': 'KDE Plasma',
            'packages': [
                'kde-plasma-desktop',
                'plasma-workspace',
                'kwin-x11',
                'konsole',
                'dolphin',
                'systemsettings',
                'plasma-desktop',
                'dbus-x11'
            ],
            'size_mb': 1800,
            'startup_cmd': 'startplasma-x11'
        },
        'mate': {
            'name': 'MATE',
            'packages': [
                'mate-desktop-environment',
                'mate-terminal',
                'caja',
                'marco',               # Window manager
                'mate-settings-daemon',
                'mate-panel',
                'dbus-x11'
            ],
            'size_mb': 700,
            'startup_cmd': 'mate-session'
        },
        'cinnamon': {
            'name': 'Cinnamon',
            'packages': [
                'cinnamon-desktop-environment',
                'cinnamon',
                'nemo',
                'muffin',              # Window manager
                'cinnamon-settings-daemon',
                'dbus-x11'
            ],
            'size_mb': 900,
            'startup_cmd': 'cinnamon-session'
        },
        'lxde': {
            'name': 'LXDE',
            'packages': [
                'lxde',
                'lxterminal',
                'pcmanfm',
                'openbox',             # Window manager
                'lxpanel',
                'dbus-x11'
            ],
            'size_mb': 300,
            'startup_cmd': 'startlxde'
        },
        'lxqt': {
            'name': 'LXQt',
            'packages': [
                'lxqt',
                'qterminal',
                'pcmanfm-qt',
                'openbox',             # Window manager
                'lxqt-panel',
                'dbus-x11'
            ],
            'size_mb': 400,
            'startup_cmd': 'startlxqt'
        }
    }

    def __init__(self):
        self.distro_info = self._detect_distro()

    def _detect_distro(self) -> Dict:
        """Detects Linux distribution"""
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
            logger.error(f"Error detecting distribution: {e}")
            return {'id': 'unknown', 'version': 'unknown', 'name': 'Unknown'}

    def get_available_des(self) -> List[Dict]:
        """Returns list of DEs available for installation"""
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
        """Checks if a DE is installed"""
        if de_id not in self.DE_PACKAGES:
            return False

        de_info = self.DE_PACKAGES[de_id]
        packages = de_info['packages']
        if not packages:
            return False

        main_package = packages[0]

        try:
            result = subprocess.run(
                ['dpkg', '-l', main_package],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0 and 'ii' in result.stdout

        except Exception as e:
            logger.error(f"Error checking installation of {de_id}: {e}")
            return False

    def install_de(self, de_id: str, progress_callback=None) -> Tuple[bool, str]:
        """
        Install a desktop environment

        Args:
            de_id: Desktop environment ID
            progress_callback: Callback function for progress (progress, message)

        Returns:
            Tuple (success, message)
        """
        def log(progress, message):
            if progress_callback:
                progress_callback(progress, message)
            logger.info(message)

        if de_id not in self.DE_PACKAGES:
            return False, f"Desktop environment '{de_id}' not supported"

        if self.is_de_installed(de_id):
            msg = f"{self.DE_PACKAGES[de_id]['name']} is already installed"
            logger.info(msg)
            log(100, f"OK {msg}")
            return True, msg

        de_info = self.DE_PACKAGES[de_id]
        packages = de_info['packages']

        if not packages:
            return False, f"No packages defined for {de_id}"

        try:
            log(5, f"→ Checking disk space...")

            # Check disk space
            has_space, required, available = self.check_disk_space(de_id)
            if not has_space:
                error_msg = f"Insufficient space. Required: {required}MB, Available: {available}MB"
                log(0, f"X {error_msg}")
                return False, error_msg

            log(5, f" OK Available space: {available}MB (required: {required}MB)")
            log(5, "")

            # Update package manager cache
            log(10, "→ Updating package cache...")

            # Get appropriate elevation command (pkexec or sudo)
            priv_method, priv_cmd = get_privilege_command()
            auth_msg = "pkexec" if priv_method == "pkexec" else "sudo"
            log(10, f" WARNING You will be asked to authenticate ({auth_msg})")

            log(10, f"  $ {auth_msg} apt-get update")
            update_result = subprocess.run(
                priv_cmd + ['/usr/bin/apt-get', 'update'],
                capture_output=True,
                text=True,
                timeout=120
            )

            if update_result.returncode != 0:
                logger.warning(f"Update returned code {update_result.returncode}")
                log(10, f" WARNING Warning: Update returned code {update_result.returncode}")
            else:
                log(15, "OK Cache updated successfully")

            log(15, "")

            # Install packages
            log(20, f"→ Installing {de_info['name']}...")
            log(20, f" Packets: {', '.join(packages)}")
            log(20, "")

            # If we are using sudo and have already authenticated, there is no need to authenticate again
            if priv_method == "pkexec":
                log(20, " WARNING You will be asked to authenticate again")

            log(20, f"  $ {auth_msg} apt-get install -y {' '.join(packages)}")
            log(20, "")
            log(30, "→ Downloading and installing packages...")
            if priv_method == "pkexec":
                log(30, " (pkexec blocks output - monitoring /var/log/apt/term.log)")
            log(30, "")

            # Monitor log files in real time
            import time
            import os

            log_file = '/var/log/apt/term.log'
            cmd = priv_cmd + ['/usr/bin/apt-get', 'install', '-y', '--no-install-recommends'] + packages

            try:
                initial_size = os.path.getsize(log_file)
            except:
                initial_size = 0

            # Run in background (stdout goes to /dev/null because pkexec blocks it)
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Monitor log file in real time
            progress = 30
            last_position = initial_size
            last_log_time = time.time()

            try:
                while process.poll() is None: # While process is running
                    time.sleep(1) # Check every 1 second

                    # Every 5 seconds, show that you are alive
                    if time.time() - last_log_time > 5:
                        log(progress, " ... installing (process running)...")
                        last_log_time = time.time()

                    try:
                        with open(log_file, 'r') as f:
                            f.seek(last_position)
                            new_lines = f.readlines()
                            last_position = f.tell()

                            for line in new_lines:
                                line = line.rstrip()
                                if line and progress < 90:
                                    # Filter relevant apt output
                                    if any(kw in line for kw in ['Unpacking', 'Preparing', 'Configuring', 'Setting up']):
                                        log(progress, f"  {line[:100]}")
                                        progress = min(progress + 2, 90)
                                        last_log_time = time.time()
                                    elif any(kw in line for kw in ['Get:', 'Fetched', 'Downloaded']):
                                        if 'Get:' in line:
                                            log(progress, f"  {line[:100]}")
                                        progress = min(progress + 1, 90)
                                        last_log_time = time.time()
                                    elif any(kw in line for kw in ['error', 'E:', 'Err:']):
                                        log(progress, f"  X {line[:150]}")
                                        last_log_time = time.time()
                    except Exception as e:
                        logger.debug(f"Error reading log: {e}")

                # Process finished, get return code
                returncode = process.wait()

                if returncode != 0:
                    error_msg = f"Installation failed (code: {returncode})"
                    logger.error(error_msg)
                    log(progress, f"X {error_msg}")
                    return False, error_msg

            except Exception as e:
                logger.error(f"Error during installation: {e}")
                try:
                    process.kill()
                except:
                    pass
                raise

            log(90, "")
            log(90, "OK Packages installed successfully")
            log(95, f"  OK {de_info['name']} configurado")
            log(100, "")
            log(100, f"OK {de_info['name']} installed successfully!")

            logger.info(f"{de_info['name']} installed successfully")
            return True, f"{de_info['name']} installed successfully"

        except subprocess.TimeoutExpired:
            error_msg = f"Timeout when installing {de_info['name']} (30 minutes)"
            logger.error(error_msg)
            log(0, f"X {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"Error installing {de_info['name']}: {e}"
            logger.error(error_msg)
            log(0, f"X {error_msg}")
            return False, error_msg

    def get_de_info(self, de_id: str) -> Optional[Dict]:
        """Returns information about a specific DE"""
        if de_id in self.DE_PACKAGES:
            info = self.DE_PACKAGES[de_id].copy()
            info['id'] = de_id
            info['installed'] = self.is_de_installed(de_id)
            return info

        return None

    def get_de_startup_command(self, de_id: str) -> Optional[str]:
        """Returns the initialization command of a DE"""
        if de_id in self.DE_PACKAGES:
            return self.DE_PACKAGES[de_id]['startup_cmd']

        return None

    def check_disk_space(self, de_id: str) -> Tuple[bool, int, int]:
        """
        Check if there is enough disk space

        Returns:
            Tuple (enough, required_mb, available_mb)
        """
        import shutil

        if de_id not in self.DE_PACKAGES:
            return False, 0, 0

        required_mb = self.DE_PACKAGES[de_id]['size_mb']

        try:
            stat = shutil.disk_usage('/')
            available_mb = stat.free // (1024 * 1024)

            # Add 20% safety margin
            required_with_margin = int(required_mb * 1.2)

            return available_mb >= required_with_margin, required_with_margin, available_mb

        except Exception as e:
            logger.error(f"Error checking disk space: {e}")
            return False, required_mb, 0
