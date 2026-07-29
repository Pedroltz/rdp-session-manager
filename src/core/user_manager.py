#!/usr/bin/env python3
"""
RDP User Management Module
"""

import os
import pwd
import grp
import json
import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Optional

from utils.polkit import get_privilege_command

logger = logging.getLogger(__name__)


class RDPUser:
    """Represents an RDP user"""

    def __init__(self, username: str, uid: int, home_dir: str,
                 desktop_env: str, rdp_port: int, active: bool = False, enabled: bool = True,
                 is_superuser: bool = False, session_type: str = 'desktop',
                 app_command: str = '', app_args: str = ''):
        self.username = username
        self.uid = uid
        self.home_dir = home_dir
        self.desktop_env = desktop_env
        self.rdp_port = rdp_port
        self.active = active
        self.enabled = enabled # Whether the account is enabled (not blocked)
        self.is_superuser = is_superuser # Whether the user has sudo privileges
        self.session_type = session_type  # 'desktop', 'remoteapp', ou 'winege-remoteapp'
        self.app_command = app_command # App command for RemoteApp (ex: 'firefox') or .exe path for WineGE
        self.app_args = app_args # App arguments (e.g. '--private-window')

    def to_dict(self) -> Dict:
        """Converts to dictionary"""
        return {
            'username': self.username,
            'uid': self.uid,
            'home_dir': self.home_dir,
            'desktop_env': self.desktop_env,
            'rdp_port': self.rdp_port,
            'active': self.active,
            'enabled': self.enabled,
            'is_superuser': self.is_superuser,
            'session_type': self.session_type,
            'app_command': self.app_command,
            'app_args': self.app_args
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'RDPUser':
        """Create instance from dictionary"""
        return cls(**data)


class UserManager:
    """RDP User Manager"""

    # Initial UID for RDP users (outside the range of normal users)
    RDP_UID_START = 5000

    # User state cache (enabled/disabled)
    # Used when we are not allowed to check /etc/shadow
    _user_states_cache = {}
    RDP_GID_NAME = "rdp-users"

    def __init__(self, app_config=None, rdp_users_home: str = "/opt/rdp-users"):
        self.app_config = app_config
        self.rdp_users_home = Path(rdp_users_home)
        self.config_file = self.rdp_users_home / "users.conf"
        # Persistent cache of user states
        self.states_cache_file = Path.home() / ".config" / "rdp-session-manager" / "user_states.json"
        self._ensure_base_setup()
        self._load_states_cache()

    def _ensure_base_setup(self):
        """Ensures that the base structure exists"""
        try:
            # Create base directory if it doesn't exist
            if not self.rdp_users_home.exists():
                logger.info(f"Creating base directory: {self.rdp_users_home}")
                # Will be created via PolicyKit helper

            # Ensure that the group rdp-users exists
            self._ensure_rdp_group()

        except Exception as e:
            logger.error(f"Error configuring base structure: {e}")

    def _ensure_rdp_group(self) -> int:
        """Ensures that the group rdp-users exists"""
        try:
            group = grp.getgrnam(self.RDP_GID_NAME)
            return group.gr_gid
        except KeyError:
            # Group does not exist, needs to be created via PolicyKit
            logger.warning(f"Group {self.RDP_GID_NAME} does not exist")
            return -1

    def _load_states_cache(self):
        """Loads the persistent cache of user states"""
        try:
            if self.states_cache_file.exists():
                with open(self.states_cache_file, 'r') as f:
                    cached_states = json.load(f)
                    # Update in-memory cache
                    UserManager._user_states_cache.update(cached_states)
                    logger.debug(f"State cache loaded: {cached_states}")
        except Exception as e:
            logger.warning(f"Error loading state cache: {e}")

    def _save_states_cache(self):
        """Save the user state cache to a file"""
        try:
            # Create directory if it doesn't exist
            self.states_cache_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.states_cache_file, 'w') as f:
                json.dump(UserManager._user_states_cache, f, indent=2)
                logger.debug(f"Saved state cache: {UserManager._user_states_cache}")
        except Exception as e:
            logger.error(f"Error saving state cache: {e}")

    def _get_next_uid(self) -> int:
        """Gets the next available UID for RDP users"""
        existing_uids = [user.uid for user in self.list_users()]

        uid = self.RDP_UID_START
        while uid in existing_uids:
            uid += 1

        return uid

    def create_user(self, username: str, password: str, desktop_env: str,
                   full_name: str = "", session_type: str = 'desktop',
                   app_command: str = '', app_args: str = '', log_callback=None) -> Optional[RDPUser]:
        """
        Create a new RDP user

        Args:
            username: Username
            password: User password
            desktop_env: Desktop environment (gnome, xfce, kde) - only used if session_type='desktop'
            full_name: User's full name
            session_type: Session type ('desktop', 'remoteapp', or 'winege-remoteapp')
            app_command: Application command for RemoteApp (ex: 'firefox') or .exe path for WineGE
            app_args: Application arguments (ex: '--private-window')

        Returns:
            RDPUser if successful, None if failed
        """
        logger.info("=" * 70)
        logger.info("USER_MANAGER: Create_user() Method CALLED")
        logger.info(f"  - Username: {username}")
        logger.info(f"  - Session Type: {session_type}")
        if session_type == 'desktop':
            logger.info(f"  - Desktop ENV: {desktop_env}")
        else:
            logger.info(f"  - App Command: {app_command}")
            logger.info(f"  - App Args: {app_args}")
        logger.info(f"  - Full name: {full_name}")
        logger.info("=" * 70)

        try:
            def log(msg):
                logger.info(f"USER_MANAGER: {msg}")
                if log_callback:
                    log_callback(msg)

            # Validate username
            log("→ Validating username...")
            if not self._validate_username(username):
                logger.error(f"Invalid username: {username}")
                raise ValueError(f"Invalid username: {username}")
            log("OK Valid username")

            # Check if user already exists
            log("→ Checking if user already exists...")
            if self.user_exists(username):
                logger.error(f"User already exists: {username}")
                raise ValueError(f"User already exists: {username}")
            log("OK User available")

            # Get global UID and port
            log("→ Alocando UID...")
            uid = self._get_next_uid()
            home_dir = str(self.rdp_users_home / username)

            # Get port from global configuration
            rdp_port = self.app_config.get_default_rdp_port() if self.app_config else 3389

            log(f"  UID: {uid}")
            log(f" RDP port: {rdp_port} (global port)")
            log(f"  Home: {home_dir}")

            # Create group rdp-users if it does not exist
            log("")
            log("→ Checking group rdp-users...")
            self._ensure_rdp_group_exists(log_callback=log)

            # Create base directory if it doesn't exist
            log("")
            log("→ Checking base directory...")
            self._create_base_directory(log_callback=log)

            # Create user via pkexec
            log("")
            log("→ Creating user in the system...")
            log(" WARNING You will be asked to authenticate (pkexec)")
            success = self._create_system_user(username, password, uid, home_dir, full_name, desktop_env,
                                               session_type, app_command, app_args, log_callback=log)

            if not success:
                raise Exception("Failed to create user in the system")

            rdp_user = RDPUser(
                username=username,
                uid=uid,
                home_dir=home_dir,
                desktop_env=desktop_env,
                rdp_port=rdp_port,
                active=False,
                is_superuser=False, # New users do not have sudo by default
                session_type=session_type,
                app_command=app_command,
                app_args=app_args
            )

            log("")
            log("OK User created in the system successfully!")
            logger.info("=" * 70)
            logger.info(f"USER_MANAGER: SUCCESS - RDP user created!")
            logger.info(f"  - Username: {username}")
            logger.info(f"  - UID: {uid}")
            logger.info(f" - RDP Port: {rdp_port}")
            logger.info(f"  - Home: {home_dir}")
            logger.info(f"  - Desktop ENV: {desktop_env}")
            logger.info("=" * 70)

            # Add to cache as enabled (new users are created enabled)
            UserManager._user_states_cache[username] = True
            self._save_states_cache()

            return rdp_user

        except Exception as e:
            logger.error("=" * 70)
            logger.error(f"USER_MANAGER: ERROR creating user {username}")
            logger.error(f" - Exception: {type(e).__name__}")
            logger.error(f" - Message: {e}")
            logger.error("=" * 70)
            if log_callback:
                log_callback(f"X ERROR: {e}")
            raise

    def _ensure_rdp_group_exists(self, log_callback=None):
        """Ensures that the group rdp-users exists"""
        try:
            grp.getgrnam(self.RDP_GID_NAME)
            logger.info(f"Group {self.RDP_GID_NAME} already exists")
            if log_callback:
                log_callback(f" OK Group '{self.RDP_GID_NAME}' already exists")
        except KeyError:
            # Create group
            logger.info(f"Creating group {self.RDP_GID_NAME}...")

            # Get appropriate elevation command (pkexec or sudo)
            priv_method, priv_cmd = get_privilege_command()
            auth_msg = "pkexec" if priv_method == "pkexec" else "sudo"

            if log_callback:
                log_callback(f" → Creating group '{self.RDP_GID_NAME}'...")
                log_callback(f" WARNING You will be asked to authenticate ({auth_msg})")
                log_callback(f"  $ {auth_msg} /usr/sbin/groupadd {self.RDP_GID_NAME}")

            result = subprocess.run(
                priv_cmd + ['/usr/sbin/groupadd', self.RDP_GID_NAME],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                # Check if it was canceled by the user
                if result.returncode == 126:
                    error_msg = "Authentication canceled by user"
                elif result.returncode == 127:
                    error_msg = f"{auth_msg} not found"
                else:
                    error_msg = f"Code: {result.returncode}, stderr: {result.stderr}"

                logger.error(f"Failed to create group rdp-users: {error_msg}")
                raise Exception(f"Failed to create group rdp-users: {error_msg}")

            if log_callback:
                log_callback(f" OK Group '{self.RDP_GID_NAME}' created successfully")

    def _create_base_directory(self, log_callback=None):
        """Create base directory /opt/rdp-users"""
        if not self.rdp_users_home.exists():
            logger.info(f"Creating base directory {self.rdp_users_home}...")

            # Get appropriate elevation command (pkexec or sudo)
            priv_method, priv_cmd = get_privilege_command()
            auth_msg = "pkexec" if priv_method == "pkexec" else "sudo"

            if log_callback:
                log_callback(f" → Creating directory {self.rdp_users_home}...")
                log_callback(f" WARNING You will be asked to authenticate ({auth_msg})")
                log_callback(f"  $ {auth_msg} mkdir -p {self.rdp_users_home}")

            result = subprocess.run(
                priv_cmd + ['/usr/bin/mkdir', '-p', str(self.rdp_users_home)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                if result.returncode == 126:
                    error_msg = "Authentication canceled by user"
                elif result.returncode == 127:
                    error_msg = f"{auth_msg} not found"
                else:
                    error_msg = f"Code: {result.returncode}, stderr: {result.stderr}"

                logger.error(f"Failed to create directory: {error_msg}")
                raise Exception(f"Failed to create directory /opt/rdp-users: {error_msg}")

            # Set permissions
            if log_callback:
                log_callback(f"  $ {auth_msg} chmod 755 {self.rdp_users_home}")

            chmod_result = subprocess.run(
                priv_cmd + ['/usr/bin/chmod', '755', str(self.rdp_users_home)],
                capture_output=True,
                text=True,
                timeout=30
            )

            if chmod_result.returncode != 0:
                logger.warning(f"Warning when setting permissions: {chmod_result.stderr}")

            if log_callback:
                log_callback(f" OK Directory created successfully")
        else:
            if log_callback:
                log_callback(f" OK Directory {self.rdp_users_home} already exists")

    def _create_system_user(self, username: str, password: str, uid: int,
                           home_dir: str, full_name: str, desktop_env: str,
                           session_type: str = 'desktop', app_command: str = '',
                           app_args: str = '', log_callback=None) -> bool:
        """Create user on the system via pkexec/sudo using helper script"""
        try:
            # Get helper script path
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            create_script = script_dir / "create-rdp-user.sh"
            password_script = script_dir / "set-user-password.sh"

            # Get appropriate elevation command (pkexec or sudo)
            priv_method, priv_cmd = get_privilege_command()
            auth_msg = "pkexec" if priv_method == "pkexec" else "sudo"

            # Map desktop_env to DE command (only used for desktop mode)
            de_commands = {
                'gnome': 'gnome-session',
                'xfce': 'startxfce4',
                'xfce4': 'startxfce4',
                'kde': 'startplasma-x11',
                'plasma': 'startplasma-x11',
                'mate': 'mate-session',
                'cinnamon': 'cinnamon-session',
                'lxde': 'startlxde',
                'lxqt': 'startlxqt',
            }
            de_command = de_commands.get(desktop_env.lower(), 'startxfce4')

            if log_callback:
                log_callback(f" → Creating user and configuring system...")
                log_callback(f" WARNING You will be asked to authenticate ({auth_msg})")

            # Run user creation script
            # Passar: username, uid, home_dir, full_name, session_type, de_command_or_app, app_args
            if session_type in ['remoteapp', 'winege-remoteapp']:
                session_command = app_command
                extra_args = app_args
            else:
                session_command = de_command
                extra_args = ""

            cmd = priv_cmd + [
                str(create_script),
                username,
                str(uid),
                home_dir,
                full_name or "",
                session_type,  # 'desktop' ou 'remoteapp'
                session_command, # DE or app command
                extra_args # App args (empty for desktop)
            ]

            logger.info(f"Running helper script: {create_script.name}")

            # For WineGE, we need a longer timeout (download + setup = ~15min)
            timeout_seconds = 1200 if session_type == 'winege-remoteapp' else 30
            if session_type == 'winege-remoteapp':
                logger.info(f" WARNING WineGE may take 10-15 minutes to download and install")

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_seconds)

            if result.returncode != 0:
                # Check error code
                if result.returncode == 126:
                    error_msg = "Authentication canceled by user"
                elif result.returncode == 127:
                    error_msg = "Script helper not found"
                else:
                    error_msg = f"Code: {result.returncode}, Error: {result.stderr.strip()}"

                logger.error(f"User creation failed: {error_msg}")
                if log_callback:
                    log_callback(f" X Error creating: {error_msg}")
                return False

            # Show script output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    logger.info(f"  {line}")
                    if log_callback:
                        log_callback(f"  {line}")

            # Set password
            if log_callback:
                log_callback(f" → Setting password...")
                # Only warn about authentication again if it is pkexec
                if priv_method == "pkexec":
                    log_callback(f" WARNING You will be asked to authenticate again")

            echo_proc = subprocess.Popen(
                ['echo', f'{username}:{password}'],
                stdout=subprocess.PIPE
            )

            passwd_proc = subprocess.Popen(
                priv_cmd + [str(password_script)],
                stdin=echo_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            echo_proc.stdout.close()
            stdout, stderr = passwd_proc.communicate()

            if passwd_proc.returncode != 0:
                # Check error code
                if passwd_proc.returncode == 126:
                    error_msg = "Authentication canceled by user"
                else:
                    error_msg = f"Code: {passwd_proc.returncode}, stderr: {stderr.decode().strip()}"

                logger.error(f"Password setting failed: {error_msg}")
                if log_callback:
                    log_callback(f" X Error setting password: {error_msg}")
                return False

            if log_callback:
                log_callback(f" OK Password set successfully")

            logger.info(f"User {username} successfully created on the system")
            return True

        except Exception as e:
            logger.error(f"Error creating user in the system: {e}")
            if log_callback:
                log_callback(f" X Error: {e}")
            return False

    def get_user_processes(self, username: str) -> List[int]:
        """
        Gets list of user process PIDs

        Args:
            username: Username

        Returns:
            List of PIDs
        """
        try:
            result = subprocess.run(
                ['pgrep', '-u', username],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                # Return PIDs
                pids = [int(pid) for pid in result.stdout.strip().split('\n') if pid]
                return pids

            # If returncode != 0, there are no processes
            return []

        except Exception as e:
            logger.error(f"Error checking user processes {username}: {e}")
            return []

    def kill_user_processes(self, username: str, force: bool = False) -> bool:
        """
        Kills all processes for a user

        Args:
            username: Username
            force: If True, use SIGKILL (-9), otherwise use SIGTERM (-15)

        Returns:
            True if success
        """
        try:
            signal = '-9' if force else '-15'

            logger.info(f"Terminating user processes {username} (signal: {signal})...")

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            # First try SIGTERM
            result = subprocess.run(
                priv_cmd + ['/usr/bin/pkill', signal, '-u', username],
                capture_output=True,
                text=True,
                timeout=10
            )

            # pkill returns 0 if it found processes, 1 if not
            # Both are ok
            if result.returncode in [0, 1]:
                logger.info(f"User {username} processes terminated")
                return True
            else:
                logger.warning(f"pkill returned code {result.returncode}: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"Error terminating user processes {username}: {e}")
            return False

    def delete_user(self, username: str, remove_home: bool = True, kill_processes: bool = True) -> bool:
        """
        Remove an RDP user using helper script

        Args:
            username: Username
            remove_home: If True, removes the home directory
            kill_processes: If True, kills user processes before deleting

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                raise ValueError(f"User does not exist: {username}")

            logger.info(f"Removing RDP user: {username}")

            # Check for active processes (log only)
            active_pids = self.get_user_processes(username)
            if active_pids:
                logger.info(f"User {username} has {len(active_pids)} active processes")

            # Use helper script that groups: pkill + userdel in a single authentication
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            delete_script = script_dir / "delete-rdp-user.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            # Assemble command with flags
            cmd = priv_cmd + [str(delete_script), username]

            if remove_home:
                cmd.append('--remove-home')

            if kill_processes:
                cmd.append('--kill-processes')

            logger.info(f"Running helper script to delete {username}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Deletion failed: {result.stderr}")
                raise Exception(f"Failed to remove user: {result.stderr}")

            # Show script output
            if result.stdout:
                for line in result.stdout.strip().split('\n'):
                    logger.info(f"  {line}")

            logger.info(f"OK User {username} removed successfully")
            logger.info(f" - Removed home directory: {remove_home}")
            logger.info(f" - Terminated processes: {kill_processes}")

            # Remove from cache and persist
            if username in UserManager._user_states_cache:
                del UserManager._user_states_cache[username]
                self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Error removing user {username}: {e}")
            raise

    def lock_user(self, username: str) -> bool:
        """
        Disables (blocks) an RDP user

        Args:
            username: Username

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            logger.info(f"Disabling user: {username}")

            # Use helper script for lock
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            toggle_script = script_dir / "toggle-user-lock.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(toggle_script), username, 'lock']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to disable user: {result.stderr}")
                return False

            logger.info(f"OK User {username} successfully disabled")

            # Update cache in memory and persist to file
            UserManager._user_states_cache[username] = False
            self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Error disabling user {username}: {e}")
            return False

    def unlock_user(self, username: str) -> bool:
        """
        Enables (unblocks) an RDP user

        Args:
            username: Username

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            logger.info(f"Enabling user: {username}")

            # Use helper script to unlock
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            toggle_script = script_dir / "toggle-user-lock.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(toggle_script), username, 'unlock']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to enable user: {result.stderr}")
                return False

            logger.info(f"OK User {username} enabled successfully")

            # Update cache in memory and persist to file
            UserManager._user_states_cache[username] = True
            self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Error enabling user {username}: {e}")
            return False

    def grant_sudo(self, username: str, kill_sessions: bool = True) -> bool:
        """
        Grants superuser (sudo) privileges to an RDP user

        Args:
            username: Username
            kill_sessions: If True, kills active sessions to apply changes

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            logger.info(f"Granting sudo privileges to: {username}")

            # Check if user has active processes
            active_pids = self.get_user_processes(username)
            if active_pids and kill_sessions:
                logger.info(f"User {username} has {len(active_pids)} active processes - will be terminated")
                logger.info("IMPORTANT: Group changes only take effect after logout/login")

            # Use helper script to grant sudo
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            sudo_script = script_dir / "toggle-user-sudo.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(sudo_script), username, 'grant']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to grant sudo privileges: {result.stderr}")
                return False

            logger.info(f"OK Sudo privileges granted to {username}")

            # Terminate active sessions to force reconnection
            if active_pids and kill_sessions:
                logger.info(f"Ending {username} sessions to apply changes...")
                self.kill_user_processes(username, force=False)

            return True

        except Exception as e:
            logger.error(f"Error granting sudo privileges to {username}: {e}")
            return False

    def revoke_sudo(self, username: str, kill_sessions: bool = True) -> bool:
        """
        Revokes superuser (sudo) privileges from an RDP user

        Args:
            username: Username
            kill_sessions: If True, kills active sessions to apply changes

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            logger.info(f"Revoking sudo privileges from: {username}")

            # Check if user has active processes
            active_pids = self.get_user_processes(username)
            if active_pids and kill_sessions:
                logger.info(f"User {username} has {len(active_pids)} active processes - will be terminated")
                logger.info("IMPORTANT: Group changes only take effect after logout/login")

            # Use helper script to revoke sudo
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            sudo_script = script_dir / "toggle-user-sudo.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(sudo_script), username, 'revoke']

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to revoke sudo privileges: {result.stderr}")
                return False

            logger.info(f"OK Sudo privileges revoked from {username}")

            # Terminate active sessions to force reconnection
            if active_pids and kill_sessions:
                logger.info(f"Ending {username} sessions to apply changes...")
                self.kill_user_processes(username, force=False)

            return True

        except Exception as e:
            logger.error(f"Error revoking sudo privileges from {username}: {e}")
            return False

    def is_superuser(self, username: str) -> bool:
        """
        Checks if a user has superuser privileges (is in the sudo group)

        Args:
            username: Username

        Returns:
            True if the user has sudo privileges, False otherwise
        """
        try:
            # Use 'id -nG' to get all user groups reliably
            # This command returns all groups, including secondary ones
            result = subprocess.run(
                ['id', '-nG', username],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Get list of groups
                groups = result.stdout.strip().split()
                # Check if 'sudo' is in the list
                has_sudo = 'sudo' in groups
                logger.debug(f"User {username} groups: {groups}, has sudo: {has_sudo}")
                return has_sudo

            # If the command failed, try alternative method
            logger.warning(f"Command 'id -nG {username}' failed, trying alternative method")

            # Alternative method: check directly in the group
            sudo_group = grp.getgrnam('sudo')
            return username in sudo_group.gr_mem

        except KeyError:
            # sudo group does not exist
            logger.warning("Group 'sudo' not found on system")
            return False
        except Exception as e:
            logger.error(f"Error checking sudo privileges of {username}: {e}")
            return False

    def user_exists(self, username: str) -> bool:
        """Checks if an RDP user exists"""
        try:
            pwd.getpwnam(username)
            # Check if you are in the rdp-users group
            return True
        except KeyError:
            return False

    def _is_rdp_user(self, username: str) -> bool:
        """Checks if a user belongs to the group rdp-users"""
        try:
            group = grp.getgrnam(self.RDP_GID_NAME)
            return username in group.gr_mem
        except KeyError:
            # Group does not exist yet
            return False
        except Exception as e:
            logger.error(f"Error checking user group {username}: {e}")
            return False

    def _is_user_enabled(self, username: str) -> bool:
        """
        Checks if a user is enabled (not blocked)
        NOTE: Requires root privileges, use _check_user_enabled_from_shadow for unprivileged checking

        Args:
            username: Username

        Returns:
        True when enabled, False when locked
        """
        try:
            # Use passwd -S to check account status
            # Output format: username STATUS ....
            # STATUS: P (password set), L (locked), NP (no password)
            result = subprocess.run(
                ['passwd', '-S', username],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
            # The second word indicates the status
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    status = parts[1]
                    # 'L' indica locked (bloqueado)
                    return status != 'L'

            # By default assume it is enabled
            return True

        except Exception as e:
            logger.error(f"Error checking status of {username}: {e}")
            return True # By default assume enabled

    def _check_user_enabled_from_shadow(self, username: str) -> bool:
        """
        Checks if the user is enabled by reading /etc/shadow directly
        Use cache if you don't have permissions to check

        Args:
            username: Username

        Returns:
        True when enabled, False when locked
        """
        try:
            # Try using getent shadow (may work on some systems)
            result = subprocess.run(
                ['getent', 'shadow', username],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0 and result.stdout:
                # Formato: username:password:lastchg:min:max:warn:inactive:expire:reserved
                # If password starts with '!' or '!!' is blocked
                parts = result.stdout.strip().split(':')
                if len(parts) >= 2:
                    password_field = parts[1]
                    # Blocked if starts with '!' or '!!'
                    is_locked = password_field.startswith('!')
                    enabled = not is_locked

                    # Update cache with real value
                    UserManager._user_states_cache[username] = enabled
                    return enabled

            # If you were unable to check directly, use cache
            if username in UserManager._user_states_cache:
                logger.debug(f"Using cache for {username} status: {UserManager._user_states_cache[username]}")
                return UserManager._user_states_cache[username]

            # If it is not in the cache, assume it is enabled
            # (new users are created enabled by default)
            logger.debug(f"No cache for {username}, assuming enabled")
            return True

        except Exception as e:
            logger.debug(f"Unable to check status of {username}: {e}")
            # Try using cache
            if username in UserManager._user_states_cache:
                return UserManager._user_states_cache[username]
            return True # By default assume enabled

    def _detect_session_info(self, home_dir: str) -> tuple:
        """
        Detect user session information from .xsession file

        Returns:
            tuple: (session_type, desktop_env_or_command, app_args)
        """
        try:
            xsession_file = Path(home_dir) / '.xsession'

            if not xsession_file.exists():
                logger.warning(f"File .xsession not found in {home_dir}")
                return ('desktop', 'unknown', '')

            # Read .xsession file
            with open(xsession_file, 'r') as f:
                content = f.read()

            # Detect if it is WineGE RemoteApp
            if 'Mode: WineGE RemoteApp' in content or '.launch_winege_app.sh' in content:
                # WineGE RemoteApp mode - read .exe path
                winege_app_path = Path(home_dir) / '.winege_app_path'
                if winege_app_path.exists():
                    with open(winege_app_path, 'r') as f:
                        exe_path = f.read().strip()
                        logger.debug(f"Detected WineGE RemoteApp: {exe_path}")
                        return ('winege-remoteapp', exe_path, '')
                return ('winege-remoteapp', 'unknown', '')

            # Detect whether it is RemoteApp or Desktop (RemoteApp uses openbox)
            if 'Mode: RemoteApp' in content or 'openbox' in content:
                # RemoteApp mode - extract command from app
                for line in content.split('\n'):
                    line = line.strip()
                    if line.startswith('exec ') and not any(wm in line for wm in ['openbox', 'metacity', 'dbus-launch', 'winege']):
                        # Extract command and arguments
                        exec_cmd = line[5:].strip()  # Remove "exec "
                        parts = exec_cmd.split(maxsplit=1)
                        app_command = parts[0] if parts else ''
                        app_args = parts[1] if len(parts) > 1 else ''
                        logger.debug(f"Detected RemoteApp: {app_command} {app_args}")
                        return ('remoteapp', app_command, app_args)
                return ('remoteapp', 'unknown', '')
            else:
                # Desktop mode - detect DE
                de_commands = {
                    'startlxde': 'lxde',
                    'startlxqt': 'lxqt',
                    'startxfce4': 'xfce',
                    'mate-session': 'mate',
                    'cinnamon-session': 'cinnamon',
                    'gnome-session': 'gnome',
                    'startplasma-x11': 'kde'
                }

                for command, de_id in de_commands.items():
                    if command in content:
                        logger.debug(f"Detected DE for {home_dir}: {de_id} (command: {command})")
                        return ('desktop', de_id, '')

                logger.warning(f"DE command not recognized in {xsession_file}")
                return ('desktop', 'unknown', '')

        except Exception as e:
            logger.error(f"Error detecting {home_dir} session: {e}")
            return ('desktop', 'unknown', '')

    def _detect_desktop_env(self, home_dir: str) -> str:
        """Detects the Desktop Environment by reading the .xsession file"""
        session_type, desktop_env_or_cmd, _ = self._detect_session_info(home_dir)
        if session_type in ['remoteapp', 'winege-remoteapp']:
            return session_type # For RemoteApp users, returns type as DE
        return desktop_env_or_cmd

    def _detect_rdp_port(self, uid: int) -> int:
        """Detect RDP port based on global configuration"""
        # Use global configuration port (all users on the same port)
        if self.app_config:
            return self.app_config.get_default_rdp_port()
        return 3389  # Fallback

    def list_users(self) -> List[RDPUser]:
        """List all RDP users"""
        users = []

        try:
            # Check if the group rdp-users exists
            try:
                rdp_group = grp.getgrnam(self.RDP_GID_NAME)
            except KeyError:
                # Group does not exist, there are no RDP users yet
                return users

            # List only users from the rdp-users group
            for user_info in pwd.getpwall():
                # Check if the user is in the rdp-users group
                if self._is_rdp_user(user_info.pw_name) or user_info.pw_gid == rdp_group.gr_gid:
                    # Detect session information (type, DE/app, args)
                    session_type, desktop_env_or_cmd, app_args = self._detect_session_info(user_info.pw_dir)

                    # For desktop mode, desktop_env_or_cmd is the DE
                    # For remoteapp/winege-remoteapp mode, desktop_env_or_cmd is the app command or .exe
                    if session_type in ['remoteapp', 'winege-remoteapp']:
                        desktop_env = session_type
                        app_command = desktop_env_or_cmd
                    else:
                        desktop_env = desktop_env_or_cmd
                        app_command = ''
                        app_args = ''

                    # Detect RDP port based on UID
                    rdp_port = self._detect_rdp_port(user_info.pw_uid)

                    # Check if user is enabled through /etc/shadow
                    # (does not require privileges to read if the file has correct permissions)
                    is_enabled = self._check_user_enabled_from_shadow(user_info.pw_name)

                    # Check if user has sudo privileges
                    has_sudo = self.is_superuser(user_info.pw_name)

                    rdp_user = RDPUser(
                        username=user_info.pw_name,
                        uid=user_info.pw_uid,
                        home_dir=user_info.pw_dir,
                        desktop_env=desktop_env,
                        rdp_port=rdp_port,
                        active=False, # TODO: check status
                        enabled=is_enabled,
                        is_superuser=has_sudo,
                        session_type=session_type,
                        app_command=app_command,
                        app_args=app_args
                    )
                    users.append(rdp_user)

        except Exception as e:
            logger.error(f"Error listing users: {e}")

        return users

    def get_user(self, username: str) -> Optional[RDPUser]:
        """Gets information from a specific user"""
        for user in self.list_users():
            if user.username == username:
                return user
        return None

    def _validate_username(self, username: str) -> bool:
        """Validates username"""
        import re

        # List of system reserved usernames
        RESERVED_USERNAMES = {
            'root', 'admin', 'administrator', 'daemon', 'bin', 'sys', 'sync',
            'games', 'man', 'lp', 'mail', 'news', 'uucp', 'proxy', 'www-data',
            'backup', 'list', 'irc', 'gnats', 'nobody', 'systemd-network',
            'systemd-resolve', 'messagebus', 'systemd-timesync', 'syslog',
            'avahi-autoipd', 'usbmux', 'dnsmasq', 'rtkit', 'cups-pk-helper',
            'speech-dispatcher', 'avahi', 'pulse', 'saned', 'colord', 'hplip',
            'geoclue', 'gnome-initial-setup', 'gdm', 'postgres', 'mysql',
            'ftp', 'ssh', 'sshd'
        }

        # Check if it is a reserved name
        if username.lower() in RESERVED_USERNAMES:
            logger.error(f"Username '{username}' is system reserved")
            return False

        # Name must start with a letter, contain only letters, numbers, - and _
        # Length between 3 and 32 characters
        pattern = r'^[a-z][a-z0-9_-]{2,31}$'
        return bool(re.match(pattern, username))

    def change_password(self, username: str, new_password: str) -> bool:
        """
        Change an RDP user's password

        Args:
            username: Username
            new_password: New password

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            logger.info(f"Changing user password: {username}")

            # Use helper script to change password
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            password_script = script_dir / "set-user-password.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            # Use echo and pipe to pass the password
            echo_proc = subprocess.Popen(
                ['echo', f'{username}:{new_password}'],
                stdout=subprocess.PIPE
            )

            passwd_proc = subprocess.Popen(
                priv_cmd + [str(password_script)],
                stdin=echo_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            echo_proc.stdout.close()
            stdout, stderr = passwd_proc.communicate(timeout=30)

            if passwd_proc.returncode != 0:
                error_msg = stderr.decode().strip()
                logger.error(f"Failed to change password: {error_msg}")
                return False

            logger.info(f"OK Password for {username} changed successfully")
            return True

        except Exception as e:
            logger.error(f"Error changing password for {username}: {e}")
            return False

    def rename_user(self, old_username: str, new_username: str) -> bool:
        """
        Rename an RDP user

        Args:
            old_username: Current user name
            new_username: New username

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(old_username):
                logger.error(f"User does not exist: {old_username}")
                return False

            if self.user_exists(new_username):
                logger.error(f"User already exists: {new_username}")
                return False

            # Validate new name
            if not self._validate_username(new_username):
                logger.error(f"Invalid username: {new_username}")
                return False

            logger.info(f"Renaming user: {old_username} -> {new_username}")

            # Use helper script to rename user
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            rename_script = script_dir / "rename-user.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(rename_script), old_username, new_username]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to rename user: {result.stderr}")
                return False

            logger.info(f"OK User renamed: {old_username} -> {new_username}")

            # Update state cache
            if old_username in UserManager._user_states_cache:
                UserManager._user_states_cache[new_username] = UserManager._user_states_cache.pop(old_username)
                self._save_states_cache()

            return True

        except Exception as e:
            logger.error(f"Error renaming user {old_username}: {e}")
            return False

    def change_user_fullname(self, username: str, new_fullname: str) -> bool:
        """
        Change the full name (GECOS) of an RDP user

        Args:
            username: Username
            new_fullname: New full name

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            logger.info(f"Changing full name from {username} to: {new_fullname}")

            # Use helper script to change GECOS
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            chfn_script = script_dir / "change-user-fullname.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(chfn_script), username, new_fullname]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to change full name: {result.stderr}")
                return False

            logger.info(f"OK Full name of {username} changed successfully")
            return True

        except Exception as e:
            logger.error(f"Error changing full name of {username}: {e}")
            return False

    def list_user_executables(self, username: str) -> list:
        """
        List all executables available to a WineGE user

        Args:
            username: Username

        Returns:
            List of available executable paths
        """
        try:
            if not self.user_exists(username):
                return []

            user_home = self.rdp_users_home / username
            executables = []

            # Search in WindowsApps (laptops)
            windows_apps = user_home / "WindowsApps"
            if windows_apps.exists():
                for exe in windows_apps.glob("*.exe"):
                    executables.append(("WindowsApps", str(exe)))

            # Buscar instalados no Wine
            wine_prefix = user_home / ".wine" / "drive_c"
            if wine_prefix.exists():
                program_files = [
                    wine_prefix / "Program Files",
                    wine_prefix / "Program Files (x86)"
                ]

                for pf in program_files:
                    if pf.exists():
                        for exe in pf.rglob("*.exe"):
                            exe_name_lower = exe.name.lower()
                            # Filter default Windows applications and uninstallers
                            if not any(x in str(exe).lower() for x in [
                                'unins', 'uninst', 'windows nt', 'internet explorer',
                                'windows media', 'windows mail', 'windows photo',
                                'wordpad', 'notepad'
                            ]):
                                executables.append(("Wine", str(exe)))

            return executables

        except Exception as e:
            logger.error(f"Error listing executables from {username}: {e}")
            return []

    def update_winege_executable(self, username: str, new_exe_path: str) -> bool:
        """
        Updates an existing user's WineGE executable

        Args:
            username: Username
            new_exe_path: Path of the new .exe executable

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            logger.info(f"Updating WineGE executable from {username} to: {new_exe_path}")

            # Use helper script to update .exe
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            update_script = script_dir / "update-winege-exe.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(update_script), username, new_exe_path]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to update executable: {result.stderr}")
                return False

            logger.info(f"OK WineGE executable from {username} updated successfully")
            return True

        except Exception as e:
            logger.error(f"Error updating executable from {username}: {e}")
            return False

    def change_user_session_type(self, username: str, session_type: str,
                                 session_command: str = '', app_args: str = '') -> bool:
        """
        Changes the session type of an RDP user (desktop <-> remoteapp <-> winege-remoteapp)

        Args:
            username: Username
            session_type: New type ('desktop', 'remoteapp', or 'winege-remoteapp')
            session_command: Command DE (desktop), app (remoteapp), or .exe path (winege-remoteapp)
            app_args: App arguments (remoteapp/winege-remoteapp only)

        Returns:
            True if successful, False if failed
        """
        try:
            if not self.user_exists(username):
                logger.error(f"User does not exist: {username}")
                return False

            if session_type not in ['desktop', 'remoteapp', 'winege-remoteapp']:
                logger.error(f"Invalid session type: {session_type}")
                return False

            logger.info(f"Changing session type from {username} to: {session_type}")

            # Check if user has active processes
            active_pids = self.get_user_processes(username)
            if active_pids:
                logger.info(f"User {username} has {len(active_pids)} active processes - will be terminated")

            # Use helper script to change .xsession
            script_dir = Path(__file__).parent.parent.parent / "helpers"
            change_script = script_dir / "change-session-type.sh"

            # Get appropriate elevation command (pkexec or sudo)
            _, priv_cmd = get_privilege_command()

            cmd = priv_cmd + [str(change_script), username, session_type, session_command, app_args]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

            if result.returncode != 0:
                logger.error(f"Failed to change session type: {result.stderr}")
                return False

            logger.info(f"OK Session type from {username} changed to {session_type}")
            return True

        except Exception as e:
            logger.error(f"Error changing session type from {username}: {e}")
            return False
